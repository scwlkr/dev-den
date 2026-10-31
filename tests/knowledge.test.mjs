import test from "node:test";
import assert from "node:assert/strict";
import { packet, searchEvidence, advisor } from "../app/lib/knowledge.mjs";

test("packet includes compiled sections and grounded basis", () => {
  const p = packet("tobi", { question: "refactor performance", options: ["a", "b"] });
  assert.ok(p.knowledge.length > 0);
  const item = p.knowledge.flatMap((s) => s.items)[0];
  assert.ok(item.basis === "documented" || item.basis === "inferred");
  assert.ok(item.evidence_ids.length > 0);
  for (const id of item.evidence_ids) assert.ok(p.evidence.some((e) => e.id === id));
});

test("technical topics retrieve correctly", () => {
  const p = packet("tobi", { question: "COVID re-derive assumption plan", options: ["x"] });
  const texts = p.knowledge.flatMap((s) => s.items.map((i) => i.text)).join(" ");
  assert.match(texts, /re-derive|assumption/i);
});

test("nonselected foreign evidence cannot be laundered", () => {
  const p = packet("tobi", { question: "refactor", options: ["a"] });
  const ids = new Set(p.evidence.map((e) => e.id));
  for (const s of p.knowledge) for (const i of s.items) {
    for (const eid of i.evidence_ids) assert.ok(ids.has(eid), "foreign/unselected evidence id " + eid);
  }
});

test("source diversity and limits", () => {
  const p = packet("tobi", { question: "software", options: ["a"] });
  assert.ok(p.evidence.length <= 12);
  const works = new Map();
  for (const e of p.evidence) works.set(e.work, (works.get(e.work) || 0) + 1);
  for (const c of works.values()) assert.ok(c <= 2);
});

test("searchEvidence deterministic bounded no network", () => {
  const r = searchEvidence("tobi", "performance", { limit: 5 });
  assert.ok(r.results.length <= 5);
  assert.equal(r.network, false);
  assert.equal(r.source_hash_checked, true);
  assert.ok(Array.isArray(r.limitations));
});

test("narrow coverage stays explicit", () => {
  const p = packet("tobi", { question: "zzzznonexistent", options: ["a"] });
  assert.ok(Array.isArray(p.gaps) && p.gaps.length > 0);
  assert.ok(Array.isArray(p.limits));
});
