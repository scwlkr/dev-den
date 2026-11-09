// Session/event and three-round orchestration adapted from roast-room; see NOTICE.md.
import fs from "node:fs";
import path from "node:path";
import { nextStep, prompt } from "./protocol.mjs";
import { providerConfig, requestFor, invoke, Ledger } from "./providers.mjs";
export class Council {
  constructor(
    store,
    { ledger = new Ledger(), provider = invoke, config = providerConfig } = {},
  ) {
    this.store = store;
    this.ledger = ledger;
    this.provider = provider;
    this.config = config;
    this.running = new Set();
    this.pauses = new Set();
  }
  pause(id) {
    this.pauses.add(id);
    this.store.mutate(id, (s) => {
      if (s.status === "complete") return;
      s.pause_requested = true;
      if (s.status !== "running" && !s.pending) s.status = "paused";
      this.store.event(s, "pause_requested", {
        message:
          "Pause requested; an in-flight contribution will finish first.",
      });
    });
  }
  async run(id, cap = 0.75) {
    if (this.running.has(id)) throw Error("Review is already running");
    if (this.running.size)
      throw Error("One paid review at a time protects the shared budget");
    const s = this.store.read(id);
    if (s.pending)
      throw Error(
        "Unresolved paid request; inspect the runtime ledger before continuing",
      );
    if (s.status === "complete") return;
    const config = this.config(),
      lock = path.join(path.dirname(this.ledger.file), "run.lock");
    let lockFd;
    try {
      lockFd = fs.openSync(lock, "wx", 0o600);
      fs.writeFileSync(
        lockFd,
        JSON.stringify({ pid: process.pid, session: id }),
      );
    } catch {
      throw Error(
        "Another API runner owns the runtime budget. Inspect .den/run.lock if its process has stopped.",
      );
    }
    this.running.add(id);
    this.pauses.delete(id);
    try {
      this.store.mutate(id, (s) => {
        s.status = "running";
        s.pause_requested = false;
        s.provider = config.kind + ":" + config.model;
        s.reviewMode = s.reviewMode || "normal";
        s.error = null;
        this.store.event(s, "running", {
          message:
            "Prepared evidence only; no source collection during this review.",
        });
      });
      while (
        nextStep(this.store.read(id)) &&
        !this.pauses.has(id) &&
        !this.store.read(id).pause_requested
      ) {
        const session = this.store.read(id),
          step = nextStep(session),
          p = prompt(session, step),
          request = requestFor(config, p);
        const job = this.ledger.reserve(
          session,
          step.key,
          request,
          config,
          cap,
        );
        this.store.mutate(id, (s) => {
          s.pending = { ...job, key: step.key };
          s.usage.reserved += job.reservation;
          this.store.event(s, "thinking", {
            key: step.key,
            advisor: step.advisor,
            stage: step.stage,
          });
        });
        let result;
        try {
          result = await this.provider(config, request);
        } catch (e) {
          if (e.definite) {
            this.ledger.rejected(job.id);
            this.store.mutate(id, (s) => {
              s.usage.reserved -= job.reservation;
              delete s.pending;
            });
          }
          throw e;
        }
        const actual = this.ledger.finish(job.id, result, config);
        this.store.mutate(id, (s) => {
          s.usage.usd += actual;
          s.usage.reserved -= job.reservation;
          s.usage.calls++;
          delete s.pending;
          this.store.event(s, "usage", { usd: actual });
        });
        let card;
        try {
          card = JSON.parse(result.text);
        } catch {
          throw Error(
            "Provider response was charged and retained, but was not valid JSON. Correct it through the agent submission workflow; no automatic retry.",
          );
        }
        this.store.submit(id, step.key, card, { internal: true });
      }
      this.store.mutate(id, (s) => {
        if (s.status !== "complete") {
          s.status = "paused";
          this.store.event(s, "paused", {
            message:
              "Paused between contributions. Resume continues from the next missing card.",
          });
        }
      });
    } catch (e) {
      this.store.mutate(id, (s) => {
        s.status = s.pending ? "needs_review" : "paused";
        s.error = e.message;
        this.store.event(s, "error", { message: e.message });
      });
    } finally {
      this.running.delete(id);
      this.pauses.delete(id);
      fs.closeSync(lockFd);
      fs.unlinkSync(lock);
    }
  }
}
