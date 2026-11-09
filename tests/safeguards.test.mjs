import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Store } from "../app/lib/sessions.mjs";
import { ROOT } from "../app/lib/knowledge.mjs";
import { nextStep, decisionMetrics } from "../app/lib/protocol.mjs";
import { fixtureCard } from "../app/lib/demo.mjs";
import { report } from "../app/lib/report.mjs";
const brief = JSON.parse(fs.readFileSync(path.join(ROOT, "examples/todo.json"), "utf8"));
function fill(store, id) {
  let s = store.read(id), step;
  while ((step = nextStep(s))) {
    store.submit(id, step.key, fixtureCard(s, step));
    s = store.read(id);
  }
  return s;
}
test("safeguards metrics present", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dod-sg-"));
  const store = new Store(path.join(dir, "sessions"));
  const s = fill(store, store.create(brief, null, "normal").id);
  const m = decisionMetrics(s);
  assert.ok(m.recommendedOption);
  assert.equal(typeof m.spread, "number");
  assert.ok(report(s).decisionMetrics);
  fs.rmSync(dir, { recursive: true, force: true });
});
