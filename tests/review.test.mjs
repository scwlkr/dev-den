import { test } from "node:test";
import http from "node:http";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Store, publicSession } from "../app/lib/sessions.mjs";
import { ROOT, advisor, normalize } from "../app/lib/knowledge.mjs";
import {
  nextStep,
  validateCard,
  weightedScores,
  prompt,
} from "../app/lib/protocol.mjs";
import { fixtureCard } from "../app/lib/demo.mjs";
import { Ledger, cost, defaultRates } from "../app/lib/providers.mjs";
import { Council } from "../app/lib/council.mjs";
import { report, markdown } from "../app/lib/report.mjs";
import { createServer } from "../app/server.mjs";
const brief = JSON.parse(
  fs.readFileSync(path.join(ROOT, "examples/todo.json")),
);
const temp = () => fs.mkdtempSync(path.join(os.tmpdir(), "dod-review-test-"));
function fixture(fn) {
  return async () => {
    const dir = temp();
    try {
      await fn(new Store(path.join(dir, "sessions")), dir);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  };
}
function complete(store, id) {
  let step;
  while ((step = nextStep(store.read(id)))) {
    const s = store.read(id);
    store.submit(id, step.key, fixtureCard(s, step));
  }
  return store.read(id);
}
test(
  "full agent protocol, frozen first-hand evidence, real dissent, weighted report and persisted replay",
  fixture((store) => {
    const initial = store.create(brief);
    const first = nextStep(initial);
    assert.equal(Object.keys(prompt(initial, first).prior).length, 0);
    const opening = fixtureCard(initial, first);
    store.submit(initial.id, first.key, opening);
    assert.deepEqual(
      store.submit(initial.id, first.key, opening).cards[first.key],
      opening,
    );
    const s = complete(store, initial.id),
      r = report(s);
    assert.equal(s.status, "complete");
    assert.equal(Object.keys(s.cards).length, 18);
    assert.equal(r.dissent.length, 1);
    assert.equal(r.amendments.length, 1);
    assert.ok(r.verdict.experiment && r.verdict.revisit.length);
    assert.ok(
      r.sources.every(
        (e) => e.id.startsWith(e.advisor + "-") && e.url.startsWith("http"),
      ),
    );
    assert.ok(r.sources.some((e) => e.excerpt));
    assert.ok(markdown(s).includes("Simulated advisors"));
    assert.ok(markdown(s).includes("## Dissent"));
    const reopened = new Store(store.dir).read(s.id);
    assert.deepEqual(
      reopened.events.map((e) => e.seq),
      reopened.events.map((_, i) => i + 1),
    );
    assert.equal(reopened.cards.verdict.recommendation, s.brief.options[0]);
    assert.ok(
      publicSession(s).packets.dhh.evidence[0].quote.split(/\s+/).length <= 12,
    );
  }),
);
test(
  "reject wrong advisor/source, forged quote and invalid scores before publication",
  fixture((store) => {
    const s = store.create(brief),
      step = nextStep(s),
      card = fixtureCard(s, step);
    const forged = structuredClone(card);
    forged.evidence_ids = [s.packets.tobi.evidence[0].id];
    assert.throws(() => store.submit(s.id, step.key, forged), /Citation/);
    const quote = structuredClone(card);
    quote.argument = "He said “rewrite everything now”.";
    assert.throws(() => store.submit(s.id, step.key, quote), /quotations/);
    const score = structuredClone(card);
    score.scores[0].score = 11;
    assert.throws(() => store.submit(s.id, step.key, score), /number/);
    assert.equal(store.read(s.id).events.length, 1);
    assert.equal(Object.keys(store.read(s.id).cards).length, 0);
    assert.throws(() => store.submit(s.id, "debate:dhh", card), /Expected/);
  }),
);
test(
  "reject invalid briefs, duplicate seats, empty justification and traversal",
  fixture((store) => {
    assert.throws(
      () => store.create({ ...brief, options: ["Rust", "rust"] }),
      /distinct/,
    );
    assert.throws(() => store.create({ ...brief, success: "" }), /success/);
    const s = store.create(brief);
    assert.throws(
      () => store.create(brief, [...s.board.slice(0, 4), s.board[0]]),
      /distinct/,
    );
    assert.throws(
      () =>
        store.create(
          brief,
          s.board.map((a) => ({ ...a, reason: "" })),
        ),
      /reason/,
    );
    assert.throws(() => store.read("../../collection/roster"), /Invalid/);
  }),
);
test(
  "chair cannot invent unanimity or omit actual amendment",
  fixture((store) => {
    const s = store.create(brief);
    for (let i = 0; i < 5; i++) {
      const state = store.read(s.id),
        step = nextStep(state),
        card = fixtureCard(state, step);
      if (i === 1) card.recommendation = brief.options[1];
      store.submit(s.id, step.key, card);
    }
    let state = store.read(s.id),
      step = nextStep(state),
      card = fixtureCard(state, step);
    assert.throws(() => store.submit(s.id, step.key, card), /Unanimity/);
    card.unanimous = false;
    store.submit(s.id, step.key, card);
    while (nextStep(store.read(s.id)).stage !== "verdict") {
      state = store.read(s.id);
      step = nextStep(state);
      store.submit(s.id, step.key, fixtureCard(state, step));
    }
    state = store.read(s.id);
    step = nextStep(state);
    card = fixtureCard(state, step);
    card.amendments = [];
    assert.throws(() => store.submit(s.id, step.key, card), /amendment/);
  }),
);
test("cache-aware usage includes cache writes and long-context premiums", () => {
  assert.equal(
    cost({
      input_tokens: 1000,
      output_tokens: 100,
      input_tokens_details: {
        cached_tokens: 100,
        cache_write_tokens: 200,
        cache_write_tokens_details: { ttl_12h_tokens: 50 },
      },
    }),
    0.0015175,
  );
  assert.throws(
    () =>
      cost({
        input_tokens: 2,
        output_tokens: 1,
        input_tokens_details: { cached_tokens: 3 },
      }),
    /inconsistent/,
  );
});
test(
  "API workflow persists cost, 18 validated steps and does not repeat on resume",
  fixture(async (store, dir) => {
    const s = store.create(brief),
      ledger = new Ledger(path.join(dir, "usage.json"), 2);
    let calls = 0;
    const council = new Council(store, {
      ledger,
      config: () => ({
        kind: "test",
        model: "controlled",
        rates: defaultRates,
      }),
      provider: async () => {
        calls++;
        const current = store.read(s.id),
          step = nextStep(current);
        return {
          id: "controlled-" + calls,
          text: JSON.stringify(fixtureCard(current, step)),
          usage: { input_tokens: 100, output_tokens: 200 },
        };
      },
    });
    await council.run(s.id, 2);
    assert.equal(store.read(s.id).status, "complete");
    assert.equal(calls, 18);
    assert.ok(ledger.exposure() > 0);
    await council.run(s.id, 2);
    assert.equal(calls, 18);
    assert.equal(store.read(s.id).usage.reserved, 0);
  }),
);
test(
  "unknown paid outcome retains reservation and cannot be retried automatically",
  fixture(async (store, dir) => {
    const s = store.create(brief),
      ledger = new Ledger(path.join(dir, "usage.json"), 1);
    let calls = 0;
    const council = new Council(store, {
      ledger,
      config: () => ({
        kind: "test",
        model: "controlled",
        rates: defaultRates,
      }),
      provider: async () => {
        calls++;
        throw Error("Unknown connection outcome");
      },
    });
    await council.run(s.id, 1);
    assert.equal(store.read(s.id).status, "needs_review");
    assert.ok(ledger.exposure() > 0);
    await assert.rejects(() => council.run(s.id, 1), /Unresolved/);
    assert.equal(calls, 1);
    store.recover();
    assert.ok(store.read(s.id).pending);
  }),
);
test(
  "budget prevents provider call; known invalid charged card is retained without automatic retry",
  fixture(async (store, dir) => {
    const s = store.create(brief),
      ledger = new Ledger(path.join(dir, "usage.json"), 0.00001);
    let calls = 0;
    const council = new Council(store, {
      ledger,
      config: () => ({
        kind: "test",
        model: "controlled",
        rates: defaultRates,
      }),
      provider: async () => {
        calls++;
        return {
          id: "bad",
          text: "{}",
          usage: { input_tokens: 10, output_tokens: 5 },
        };
      },
    });
    await council.run(s.id, 1);
    assert.equal(calls, 0);
    assert.match(store.read(s.id).error, /Budget stop/);
    ledger.cap = 1;
    await council.run(s.id, 1);
    assert.equal(calls, 1);
    assert.equal(Object.values(ledger.read().jobs)[0].response_text, "{}");
    await council.run(s.id, 1);
    assert.equal(calls, 1);
    assert.equal(store.read(s.id).usage.calls, 1);
  }),
);
test(
  "pause waits for current contribution; resume uses only missing steps",
  fixture(async (store, dir) => {
    const s = store.create(brief),
      ledger = new Ledger(path.join(dir, "usage.json"), 2);
    let calls = 0,
      council;
    const provider = async () => {
      calls++;
      const state = store.read(s.id);
      if (calls === 1) new Council(store, { ledger }).pause(s.id);
      return {
        id: "pause-" + calls,
        text: JSON.stringify(fixtureCard(state, nextStep(state))),
        usage: { input_tokens: 100, output_tokens: 200 },
      };
    };
    council = new Council(store, {
      ledger,
      config: () => ({
        kind: "test",
        model: "controlled",
        rates: defaultRates,
      }),
      provider,
    });
    await council.run(s.id, 2);
    assert.equal(Object.keys(store.read(s.id).cards).length, 1);
    assert.equal(store.read(s.id).status, "paused");
    await council.run(s.id, 2);
    assert.equal(calls, 18);
    assert.equal(store.read(s.id).status, "complete");
  }),
);
test(
  "HTTP token/origin, loopback host, controlled workflow, reports and SSE ordinal replay",
  fixture(async (store, dir) => {
    const council = new Council(store, {
        ledger: new Ledger(path.join(dir, "usage.json"), 1),
      }),
      server = createServer({ store, council, allowDemo: true });
    await new Promise((r) => server.listen(0, "127.0.0.1", r));
    const base = "http://127.0.0.1:" + server.address().port;
    try {
      const boot = await (await fetch(base + "/api/bootstrap")).json(),
        headers = {
          "Content-Type": "application/json",
          "X-Den-Token": boot.token,
        };
      assert.equal(
        (await fetch(base + "/api/sessions", { method: "POST", body: "{}" }))
          .status,
        403,
      );
      assert.equal(
        (
          await fetch(base + "/api/sessions", {
            method: "POST",
            headers: { ...headers, Origin: "https://evil.example" },
            body: "{}",
          })
        ).status,
        403,
      );
      assert.equal(
        await new Promise((resolve) =>
          http.get(
            base + "/api/bootstrap",
            { headers: { Host: "evil.example" } },
            (r) => {
              r.resume();
              resolve(r.statusCode);
            },
          ),
        ),
        403,
      );
      const s = await (
        await fetch(base + "/api/sessions", {
          method: "POST",
          headers,
          body: JSON.stringify({ brief }),
        })
      ).json();
      await fetch(base + "/api/sessions/" + s.id + "/demo", {
        method: "POST",
        headers,
        body: "{}",
      });
      const r = await (
        await fetch(base + "/api/sessions/" + s.id + "/report")
      ).json();
      assert.equal(r.status, "complete");
      assert.equal(r.mode, "workflow-demo");
      assert.equal(
        (
          await fetch(base + "/api/sessions/" + s.id + "/report?format=md")
        ).headers.get("content-type"),
        "text/markdown; charset=utf-8",
      );
      const response = await fetch(
          base + "/api/sessions/" + s.id + "/events?after=1",
        ),
        reader = response.body.getReader();
      let text = "";
      while (!text.includes("id: 2")) {
        text += new TextDecoder().decode((await reader.read()).value);
      }
      assert.ok(!text.includes("id: 1\n"));
      await reader.cancel();
      const lateJoin = await fetch(
        base + "/api/sessions/" + s.id + "/events?after=9999",
      );
      assert.equal(lateJoin.status, 200); // server.close must also end active SSE streams.
      assert.equal((await fetch(base + "/%2e%2e%2fpackage.json")).status, 403);
      assert.ok(
        (await (await fetch(base + "/")).text()).includes("Den of Devs"),
      );
    } finally {
      await new Promise((r) => server.close(r));
    }
  }),
);

test(
  "provider adapters preserve schemas and normalize usage without network or credentials",
  fixture(async (store) => {
    const { requestFor, invoke } = await import("../app/lib/providers.mjs"),
      s = store.create(brief),
      p = prompt(s, nextStep(s)),
      savedFetch = globalThis.fetch,
      savedOpenAI = process.env.OPENAI_API_KEY,
      savedAnthropic = process.env.ANTHROPIC_API_KEY;
    let calls = 0;
    process.env.OPENAI_API_KEY = "controlled-test-only";
    process.env.ANTHROPIC_API_KEY = "controlled-test-only";
    try {
      for (const kind of ["openai", "compatible", "anthropic"]) {
        const config = {
            kind,
            model: "controlled-test",
            base: "https://controlled.invalid/v1",
            rates: defaultRates,
          },
          request = requestFor(config, p);
        assert.ok(JSON.stringify(request).includes("json_schema"));
        globalThis.fetch = async (url, init) => {
          calls++;
          assert.ok(init.body.includes("controlled-test"));
          const body =
            kind === "openai"
              ? {
                  id: "r",
                  output: [{ content: [{ type: "output_text", text: "{}" }] }],
                  usage: { input_tokens: 100, output_tokens: 20 },
                }
              : kind === "compatible"
                ? {
                    id: "r",
                    choices: [{ message: { content: "{}" } }],
                    usage: { prompt_tokens: 100, completion_tokens: 20 },
                  }
                : {
                    id: "r",
                    content: [{ type: "text", text: "{}" }],
                    usage: {
                      input_tokens: 80,
                      cache_read_input_tokens: 10,
                      cache_creation_input_tokens: 10,
                      output_tokens: 20,
                    },
                  };
          return { ok: true, json: async () => body };
        };
        const result = await invoke(config, request);
        assert.equal(result.text, "{}");
        assert.equal(result.usage.input_tokens, 100);
        assert.equal(result.usage.output_tokens, 20);
        assert.ok(cost(result.usage) > 0);
      }
      assert.equal(calls, 3);
    } finally {
      globalThis.fetch = savedFetch;
      if (savedOpenAI === undefined) delete process.env.OPENAI_API_KEY;
      else process.env.OPENAI_API_KEY = savedOpenAI;
      if (savedAnthropic === undefined) delete process.env.ANTHROPIC_API_KEY;
      else process.env.ANTHROPIC_API_KEY = savedAnthropic;
    }
  }),
);
