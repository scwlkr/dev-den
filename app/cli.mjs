#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { ROOT, metadata, recommend } from "./lib/knowledge.mjs";
import { Store } from "./lib/sessions.mjs";
import { nextStep, prompt } from "./lib/protocol.mjs";
import { Council } from "./lib/council.mjs";
import { markdown, report } from "./lib/report.mjs";
import { saveBoardPrefs, loadBoardPrefs, boardPrefPath } from "./lib/board.mjs";
const projectRoot = process.env.DEN_PROJECT_ROOT || ROOT;
const [command, ...args] = process.argv.slice(2),
  store = new Store(process.env.DEN_SESSION_DIR || path.join(projectRoot, "sessions"), projectRoot);
const json = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
try {
  let result;
  switch (command) {
    case "roster":
      result = metadata();
      break;
    case "recommend":
      result = recommend(json(args[0]));
      break;
    case "prepare": {
      let brief = json(args[0]);
      for (const file of args.slice(2)) {
        const name = path.basename(file);
        if (
          /(^\.env|\.pem$|\.key$|credentials|secrets|id_rsa)/i.test(name) ||
          /[\\/]\.ssh[\\/]/.test(path.resolve(file))
        )
          throw Error("Do not attach credential files");
        const text = fs.readFileSync(file, "utf8");
        if (
          /-----BEGIN .*PRIVATE KEY-----|sk-(?:proj-|[A-Za-z0-9]{20})|AKIA[0-9A-Z]{16}/.test(
            text,
          )
        )
          throw Error("Possible credential in project context");
        brief.contextFiles ??= [];
        brief.contextFiles.push({ name, text });
      }
      const s = store.create(
        brief,
        args[1] && args[1] !== "auto" ? json(args[1]) : undefined,
        "normal",
      );
      result = {
        id: s.id,
        board: s.board,
        room: "http://127.0.0.1:4731/#" + s.id,
        next: nextStep(s),
      };
      break;
    }
    case "quick": {
      const brief = json(args[0]);
      const board = args[1] && args[1] !== "auto" ? json(args[1]) : recommend(brief, ROOT, "quick");
      const s = store.create(brief, board, "quick");
      result = { id: s.id, mode: "quick", board: s.board, room: "http://127.0.0.1:4731/#" + s.id, next: nextStep(s) };
      break;
    }
    case "consult": {
      const brief = json(args[0]);
      const id = args[1];
      const board = [{ id, weight: 3, reason: "Single-advisor consultation requested." }];
      const s = store.create(brief, board, "consult");
      result = { id: s.id, mode: "consult", board: s.board, room: "http://127.0.0.1:4731/#" + s.id, next: nextStep(s) };
      break;
    }
    case "all": {
      const brief = json(args[0]);
      const all = metadata(projectRoot).map((a) => ({ id: a.id, weight: 1, reason: "Included in all-advisors review." }));
      const s = store.create(brief, all, "all");
      result = { id: s.id, mode: "all", board: s.board, room: "http://127.0.0.1:4731/#" + s.id, next: nextStep(s) };
      break;
    }
    case "selected": {
      const brief = json(args[0]);
      const board = args[1] && args[1] !== "auto" ? json(args[1]) : undefined;
      const s = store.create(brief, board, "selected");
      result = { id: s.id, mode: "selected", board: s.board, room: "http://127.0.0.1:4731/#" + s.id, next: nextStep(s) };
      break;
    }
    case "board": {
      let prefs;
      if (args[0] === "set" && args[1]) {
        prefs = JSON.parse(args[1]);
        saveBoardPrefs(prefs, projectRoot);
      } else {
        prefs = loadBoardPrefs(projectRoot);
      }
      result = prefs;
      break;
    }
    case "list":
      result = store.list();
      break;
    case "acknowledge-unknown": {
      const s = store.mutate(args[0], (s) => {
        if (!s.pending) throw Error("No unresolved pending request");
        const pending = s.pending;
        delete s.pending;
        s.status = "paused";
        s.error =
          "Unknown charge acknowledged; reservation retained. Supply a validated external card for " +
          pending.key;
        store.event(s, "reservation_acknowledged", {
          key: pending.key,
          message: s.error,
        });
      });
      result = {
        id: s.id,
        status: s.status,
        usage: s.usage,
        next: nextStep(s),
      };
      break;
    }
    case "packet": {
      const s = store.read(args[0]),
        step = nextStep(s);
      result = step ? { step, prompt: prompt(s, step) } : { complete: true };
      break;
    }
    case "submit": {
      const s = store.submit(args[0], args[1], json(args[2]));
      result = { id: s.id, status: s.status, next: nextStep(s) };
      break;
    }
    case "report": {
      const s = store.read(args[0]);
      if (args[1] === "json") result = report(s);
      else {
        process.stdout.write(markdown(s) + "\n");
        process.exit(0);
      }
      break;
    }
    case "run": {
      const cap = Number(args[1] || 0.75);
      if (cap > Number(process.env.DEN_RUNTIME_BUDGET || 0.75))
        throw Error("Review cap exceeds configured runtime allocation");
      const c = new Council(store);
      await c.run(args[0], cap);
      const s = store.read(args[0]);
      result = {
        id: s.id,
        status: s.status,
        error: s.error,
        usage: s.usage,
        next: nextStep(s),
      };
      break;
    }
    default:
      result = {
        usage: [
          "node app/cli.mjs roster",
          "node app/cli.mjs recommend brief.json",
          "node app/cli.mjs prepare brief.json [board.json|auto] [context-file ...]",
          "node app/cli.mjs quick brief.json",
          "node app/cli.mjs consult brief.json ADVISOR",
          "node app/cli.mjs selected brief.json board.json",
          "node app/cli.mjs all brief.json",
          "node app/cli.mjs packet SESSION",
          "node app/cli.mjs submit SESSION STAGE:ADVISOR card.json",
          "node app/cli.mjs run SESSION [review-cap-usd]",
          "node app/cli.mjs report SESSION [json]",
          "npm start",
        ],
        notice:
          "Prepared knowledge only. Run invokes a paid provider; packet/submit use the host agent and require no separate API key.",
      };
  }
  console.log(JSON.stringify(result, null, 2));
} catch (e) {
  console.error(e.message);
  process.exitCode = 1;
}
