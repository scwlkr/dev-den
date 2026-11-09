import test from "node:test";
import assert from "node:assert/strict";
import { packet, searchEvidence } from "../app/lib/knowledge.mjs";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

test("relevant compiled framework returned with all support", () => {
  const p = packet("tobi", { question: "COVID re-derive assumption plan", options: ["x"] });
  const fw = p.knowledge.find((s) => /framework/i.test(s.name)) || p.knowledge[0];
  assert.ok(fw);
  const item = fw.items.find((i) => /re-derive/i.test(i.text));
  assert.ok(item, "framework item present");
  assert.ok(item.evidence_ids.length > 0);
  for (const id of item.evidence_ids) assert.ok(p.evidence.some((e) => e.id === id));
});

test("working context includes actual text", () => {
  const p = packet("tobi", { question: "software", options: ["a"] });
  assert.ok(Array.isArray(p.working_context));
  assert.ok(p.working_context.length > 0);
  assert.ok(p.working_context[0].text.length > 20);
});

test("voice guidance comes with mapped evidence", () => {
  const p = packet("tobi", { question: "software", options: ["a"] });
  assert.ok(Array.isArray(p.voice_guidance));
  if (p.voice_guidance.length) {
    for (const v of p.voice_guidance) {
      assert.ok(v.evidence_ids.length > 0);
      for (const id of v.evidence_ids) assert.ok(p.evidence.some((e) => e.id === id));
    }
  }
});

test("technical tokens retrieve expected", () => {
  const p = packet("tobi", { question: "C++ ownership lifetimes", options: ["a"] });
  assert.ok(p.evidence.length > 0);
});

test("unrelated query discloses no match in searchEvidence", () => {
  const r = searchEvidence("tobi", "zzzzqqqqxxxx", { limit: 5 });
  assert.equal(r.no_match, true);
  assert.deepEqual(r.results, []);
});

test("searchEvidence cannot fetch", () => {
  const orig = globalThis.fetch;
  globalThis.fetch = () => { throw new Error("fetch blocked"); };
  try {
    const r = searchEvidence("tobi", "performance", { limit: 3 });
    assert.ok(Array.isArray(r.results));
  } finally {
    globalThis.fetch = orig;
  }
});

test("all advisors smoke", async () => {
  const { metadata, roster } = await import("../app/lib/knowledge.mjs");
  for (const d of roster()) {
    const p = packet(d.id, { question: "architecture testing", options: ["a","b"] });
    assert.ok(p.evidence.length > 0);
  }
});
