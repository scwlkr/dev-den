import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { ROOT, metadata, recommend } from "./lib/knowledge.mjs";
import { Store, publicSession } from "./lib/sessions.mjs";
import { Council } from "./lib/council.mjs";
import { nextStep, prompt } from "./lib/protocol.mjs";
import { report, markdown } from "./lib/report.mjs";
export function createServer({
  store = new Store(),
  council = new Council(store),
  allowDemo = process.env.DEN_DEMO === "1",
} = {}) {
  const token = crypto.randomBytes(24).toString("hex"),
    streams = new Set();
  store.recover();
  const publicDir = path.join(ROOT, "app/public");
  const server = http.createServer(async (req, res) => {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "no-referrer");
    res.setHeader("Cache-Control", "no-store");
    res.setHeader(
      "Content-Security-Policy",
      "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    );
    const send = (data, status = 200) => {
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(JSON.stringify(data));
    };
    try {
      const host = req.headers.host || "";
      if (!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host))
        return send({ error: "Loopback host required" }, 403);
      const url = new URL(req.url, "http://" + host),
        parts = url.pathname.split("/").filter(Boolean);
      if (req.method !== "GET") {
        if (
          req.headers["x-den-token"] !== token ||
          (req.headers.origin && req.headers.origin !== "http://" + host)
        )
          return send({ error: "Same-origin session token required" }, 403);
      }
      if (url.pathname === "/api/bootstrap" && req.method === "GET")
        return send({
          token,
          roster: metadata(store.root),
          sessions: store.list(),
          runtime: {
            cap: council.ledger.cap,
            exposure: council.ledger.exposure(),
          },
          demo: allowDemo,
        });
      let body = {};
      if (req.method === "POST") {
        let raw = "";
        for await (const chunk of req) {
          raw += chunk;
          if (Buffer.byteLength(raw) > 160000) throw Error("Request too large");
        }
        body = raw ? JSON.parse(raw) : {};
      }
      if (url.pathname === "/api/recommend" && req.method === "POST")
        return send(recommend(body, store.root));
      if (url.pathname === "/api/sessions" && req.method === "POST")
        return send(
          publicSession(store.create(body.brief, body.board, "agent")),
          201,
        );
      if (parts[0] === "api" && parts[1] === "sessions" && parts[2]) {
        const id = parts[2],
          s = store.read(id),
          action = parts[3];
        if (!action && req.method === "GET") return send(publicSession(s));
        if (action === "events" && req.method === "GET") {
          // Durable ordinal replay follows roast-room's session/event stream; file polling also observes CLI submissions.
          res.writeHead(200, {
            "Content-Type": "text/event-stream",
            Connection: "keep-alive",
          });
          streams.add(res);
          res.write(": connected\n\n");
          let seq = Number(
            req.headers["last-event-id"] || url.searchParams.get("after") || 0,
          );
          if (!Number.isFinite(seq)) seq = 0;
          const poll = () => {
            try {
              for (const e of store
                .read(id)
                .events.filter((e) => e.seq > seq)) {
                res.write(
                  "id: " + e.seq + "\ndata: " + JSON.stringify(e) + "\n\n",
                );
                seq = e.seq;
              }
            } catch {
              res.end();
            }
          };
          poll();
          const interval = setInterval(poll, 500),
            heartbeat = setInterval(() => res.write(": heartbeat\n\n"), 20000);
          req.on("close", () => {
            clearInterval(interval);
            clearInterval(heartbeat);
            streams.delete(res);
          });
          return;
        }
        if (action === "packet" && req.method === "GET") {
          const step = nextStep(s);
          return send(
            step ? { step, prompt: prompt(s, step) } : { complete: true },
          );
        }
        if (action === "report" && req.method === "GET") {
          if (url.searchParams.get("format") === "md") {
            res.writeHead(200, {
              "Content-Type": "text/markdown; charset=utf-8",
              "Content-Disposition": `attachment; filename="${id}.md"`,
            });
            return res.end(markdown(s));
          }
          res.setHeader(
            "Content-Disposition",
            `attachment; filename="${id}.json"`,
          );
          return send(report(s));
        }
        if (action === "start" && req.method === "POST") {
          const cap = Number(body.cap || 0.75);
          if (!Number.isFinite(cap) || cap <= 0 || cap > council.ledger.cap)
            throw Error(
              "Review cap must be positive and within the configured runtime allocation",
            );
          if (s.pending || council.running.size || s.status === "complete")
            throw Error("Review cannot start in its current state");
          void council.run(id, cap).catch((e) =>
            store.mutate(id, (s) => {
              s.status = "paused";
              s.error = e.message;
              store.event(s, "error", { message: e.message });
            }),
          );
          return send({ started: true });
        }
        if (action === "pause" && req.method === "POST") {
          council.pause(id);
          return send({ paused: true });
        }
        if (action === "submit" && req.method === "POST")
          return send(publicSession(store.submit(id, body.key, body.card)));
        if (action === "demo" && req.method === "POST" && allowDemo) {
          if (Object.keys(s.cards).length || council.running.size)
            throw Error("Workflow demo needs an empty session");
          const { fixtureCard } = await import("./lib/demo.mjs");
          let step;
          while ((step = nextStep(store.read(id)))) {
            const current = store.read(id);
            store.submit(id, step.key, fixtureCard(current, step));
          }
          store.mutate(id, (s) => {
            s.mode = "workflow-demo";
          });
          return send(publicSession(store.read(id)));
        }
      }
      if (req.method !== "GET") return send({ error: "Unknown action" }, 404);
      const pathname = decodeURIComponent(url.pathname),
        file = path.resolve(
          publicDir,
          "." + (pathname === "/" ? "/index.html" : pathname),
        ),
        relative = path.relative(publicDir, file);
      if (relative.startsWith("..") || path.isAbsolute(relative))
        return send({ error: "Invalid path" }, 403);
      if (!fs.existsSync(file) || !fs.statSync(file).isFile())
        return send({ error: "Not found" }, 404);
      const types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css",
        ".js": "text/javascript",
        ".svg": "image/svg+xml",
      };
      res.writeHead(200, {
        "Content-Type": types[path.extname(file)] || "application/octet-stream",
      });
      fs.createReadStream(file).pipe(res);
    } catch (e) {
      send(
        {
          error: e.code === "ENOENT" ? "Session or file not found" : e.message,
        },
        400,
      );
    }
  });
  const close = server.close.bind(server);
  server.close = (callback) => {
    for (const response of streams) response.end();
    return close(callback);
  };
  return server;
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const server = createServer();
  server.listen(Number(process.env.PORT || 4731), "127.0.0.1", () =>
    console.log("Den of Devs: http://127.0.0.1:" + server.address().port),
  );
  const stop = () => server.close(() => process.exit(0));
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
}
