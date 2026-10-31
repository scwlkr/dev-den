import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { tokenize, bm25 } from "./retrieval.mjs";
export const ROOT = path.resolve(import.meta.dirname, "../..");
export const normalize = (s) =>
  s
    .normalize("NFC")
    .replace(
      /[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/gu,
      " ",
    )
    .replace(/^ +| +$/g, "");
const hash = (s) => crypto.createHash("sha256").update(s).digest("hex");
const read = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const cache = new Map();
export function roster(root = ROOT) {
  return read(path.join(root, "collection/roster.json")).developers;
}
export function advisor(id, root = ROOT) {
  const key = root + id;
  if (cache.has(key)) return cache.get(key);
  const dev = roster(root).find((d) => d.id === id);
  if (!dev) throw Error("Unknown advisor");
  const base = path.join(root, ".collection/pilot", id),
    compiled = read(path.join(base, "compiled.json"));
  const evidence = [],
    works = new Map();
  for (const folder of fs.readdirSync(path.join(base, "sources"))) {
    const dir = path.join(base, "sources", folder),
      p = path.join(dir, "evidence.json");
    if (!fs.existsSync(p)) continue;
    const r = read(p);
    if (r.status !== "accepted") continue;
    const text = normalize(
      fs.readFileSync(path.join(dir, "source.txt"), "utf8"),
    );
    if (hash(text) !== r.text_sha256)
      throw Error("Prepared source hash mismatch: " + r.source_id);
    const prose = normalize(text.replace(/\[\d{2}:\d{2}:\d{2}\]/g, " "));
    const textChars = Array.from(text),
      proseChars = Array.from(prose);
    works.set(
      r.work_key || r.url,
      Math.max(
        works.get(r.work_key || r.url) || 0,
        r.coverage_words ?? r.words ?? 0,
      ),
    );
    for (const e of r.evidence) {
      const view = e.passage_view === "caption-prose-v1" ? prose : text;
      // Python offsets count Unicode code points; JavaScript indices count UTF-16 units.
      const chars =
          e.passage_view === "caption-prose-v1" ? proseChars : textChars,
        q = Array.from(e.quote),
        offset = e.passage_offset;
      if (
        e.developer !== id ||
        e.source_id !== r.source_id ||
        chars.slice(offset, offset + q.length).join("") !== e.quote
      )
        throw Error("Prepared evidence mismatch: " + e.id);
      if (
        r.source_scope &&
        !r.source_scope.normalized_ranges.some(
          ([a, b]) => a <= offset && offset + q.length <= b,
        )
      )
        throw Error("Evidence outside attributed source scope");
      if (!["sole_author", "coauthored", "speaker"].includes(e.attribution))
        throw Error("Unsupported attribution");
      if (e.attribution === "speaker") {
        const identity = (s) =>
          s
            .normalize("NFKD")
            .toLowerCase()
            .replace(/[^a-z0-9]/g, "");
        if (
          !(dev.aliases || [dev.name]).some(
            (a) => identity(a) === identity(e.speaker),
          )
        )
          throw Error("Speaker mismatch");
      }
      const url = e.source_url || r.metadata.url,
        allowed = [
          r.url,
          r.metadata.url,
          ...(r.metadata.parts || []).map((p) => p.url),
        ];
      if (!allowed.includes(url) && !allowed.includes(url.split("&t=")[0]))
        throw Error("Foreign source link");
      if (!/^https?:\/\//.test(url)) throw Error("Unsafe source link");
      evidence.push({
        ...e,
        url,
        title: r.metadata.title || r.candidate.title || r.source_id,
        date: r.extractions?.find((x) => x.date)?.date || "",
        work: r.work_key || r.url,
        caption: !!r.metadata.duration_seconds,
        source_hash: r.text_sha256,
      });
    }
  }
  const ids = new Set(evidence.map((e) => e.id));
  for (const s of compiled.sections)
    for (const i of s.items)
      if (!i.evidence_ids.length || i.evidence_ids.some((id) => !ids.has(id)))
        throw Error("Unmapped compiled knowledge");
  const result = {
    ...dev,
    evidence,
    compiled,
    works: works.size,
    words: [...works.values()].reduce((a, b) => a + b, 0),
  };
  cache.set(key, result);
  return result;
}
export function metadata(root = ROOT) {
  return roster(root).map((d) => {
    const a = advisor(d.id, root);
    return {
      id: a.id,
      name: a.name,
      focus: a.focus,
      works: a.works,
      words: a.words,
      gaps: a.compiled.gaps,
    };
  });
}
export function corpusFingerprint(id, root = ROOT) {
  const base = path.join(root, ".collection/pilot", id);
  const compiled = JSON.parse(fs.readFileSync(path.join(base, "compiled.json"), "utf8"));
  if (compiled.source_fingerprint) return compiled.source_fingerprint;
  return hash(JSON.stringify(compiled));
}

export function searchEvidence(id, query, opts = {}, root = ROOT) {
  const a = advisor(id, root);
  const limit = Math.max(1, Math.min(opts.limit || 8, 40));
  const docs = a.evidence.map((e) => tokenize(e.claim + " " + e.context + " " + e.quote));
  const scores = bm25(docs, query || "");
  const ranked = a.evidence
    .map((e, i) => ({ e, score: scores[i] }))
    .sort((x, y) => y.score - x.score || x.e.id.localeCompare(y.e.id));
  const chosen = [];
  const counts = new Map();
  for (const { e, score } of ranked) {
    if (score <= 0) continue;
    if ((counts.get(e.work) || 0) >= 2) continue;
    chosen.push({ ...e, score });
    counts.set(e.work, (counts.get(e.work) || 0) + 1);
    if (chosen.length >= limit) break;
  }
  const no_match = chosen.length === 0;
  const result = {
    advisor: a.id,
    query: query || "",
    results: chosen,
    coverage: { works: a.works, words: a.words, evidence_count: a.evidence.length },
    limitations: a.compiled.gaps,
    source_hash_checked: true,
    network: false,
    no_match,
  };
  return result;
}

export function packet(id, brief, root = ROOT, options = {}) {
  const a = advisor(id, root);
  const briefText = JSON.stringify(brief || {});
  const query = briefText;
  const BUDGET_CHARS = options.budget || 56000;
  if (typeof BUDGET_CHARS !== "number" || !Number.isFinite(BUDGET_CHARS) || BUDGET_CHARS < 1000) throw Error("Invalid budget");

  // Rank compiled nodes by question and section.
  const sections = a.compiled.sections || [];
  const nodeDocs = [];
  const nodeList = [];
  for (const s of sections) {
    for (const it of s.items) {
      nodeList.push({ section: s.name, item: it });
      nodeDocs.push(tokenize(it.text));
    }
  }
  const nodeScores = bm25(nodeDocs, query);
  const rankedNodes = nodeList.map((n, i) => ({ ...n, score: nodeScores[i] }))
    .sort((x, y) => y.score - x.score);

  // Select nodes until char budget, ensuring _hot and voice included.
  const selectedNodes = [];
  const buildResult = (nodes) => {
    const neededIds = new Set();
    for (const n of nodes) for (const eid of (n.item.evidence_ids || [])) neededIds.add(eid);
    const chosen = a.evidence.filter((e) => neededIds.has(e.id));
    const chosenIds = new Set(chosen.map((e) => e.id));
    const sectionMap = new Map();
    for (const n of nodes) {
      const ids = n.item.evidence_ids || [];
      if (!ids.every((eid) => chosenIds.has(eid))) continue;
      if (!sectionMap.has(n.section)) sectionMap.set(n.section, []);
      sectionMap.get(n.section).push({ text: n.item.text, basis: n.item.basis, evidence_ids: [...ids] });
    }
    return {
      id: a.id, name: a.name, focus: a.focus,
      coverage: { works: a.works, words: a.words },
      gaps: a.compiled.gaps,
      working_context: sectionMap.get("_hot") || [],
      voice_guidance: sectionMap.get("voice") || [],
      knowledge: [...sectionMap.entries()].filter(([n])=>n!=="_hot"&&n!=="voice").map(([name,items])=>({name,items})),
      evidence: chosen,
      limits: a.compiled.gaps,
      omitted_sections: [],
      corpusFingerprint: corpusFingerprint(a.id, root),
    };
  };
  const tryAdd = (n) => {
    if (selectedNodes.includes(n)) return;
    selectedNodes.push(n);
    const r = buildResult(selectedNodes);
    if (JSON.stringify(r).length <= BUDGET_CHARS - 256) return true;
    selectedNodes.pop();
    return false;
  };
  // Reserve: a few from each key section first
  for (const sec of ["_hot","voice"]) {
    let count=0;
    for (const n of rankedNodes) {
      if (n.section!==sec) continue;
      if (count>=3) break;
      if (tryAdd(n)) count++;
    }
  }
  // then relevant nodes by score
  for (const n of rankedNodes) {
    if (selectedNodes.includes(n)) continue;
    tryAdd(n);
  }
  const result = buildResult(selectedNodes);
  const omittedSections = sections.map((s) => s.name).filter((name) => !(result.knowledge.some(k=>k.name===name) || (result.working_context.length && name==="_hot") || (result.voice_guidance.length && name==="voice")));
  result.omitted_sections = omittedSections;
  result.limits = [...a.compiled.gaps, ...(omittedSections.length ? ["Omitted sections: " + omittedSections.join(", ")] : [])];
  result.fingerprint = hash(JSON.stringify(result));
  return result;
}

export function recommend(brief, root = ROOT, mode = "normal") {
  const rosterList = roster(root);
  const q = JSON.stringify(brief || {}).toLowerCase();
  const qTokens = new Set(q.match(/[a-z]{3,}/g) || []);
  const scored = rosterList.map((d) => {
    const a = advisor(d.id, root);
    const text = (d.focus + " " + (a.compiled.sections || []).map((s) => s.items.map((i) => i.text).join(" ")).join(" ")).toLowerCase();
    let score = 0;
    for (const t of qTokens) if (text.includes(t)) score += 1;
    return { d, a, score };
  }).sort((x, y) => y.score - x.score);
  const pick = (arr, n) => arr.slice(0, n);
  const top = scored.filter((s) => s.score > 0).slice(0, 5);
  const fallback = scored.slice(0, 5);
  const chosen = (top.length ? top : fallback).slice(0, 5);
  const ids = chosen.map((c) => c.d.id);
  // ensure downside/general lens and differing perspective: append a lower-scored advisor if not present
  if (chosen.length < 5) {
    for (const s of scored) {
      if (!ids.includes(s.d.id)) { chosen.push(s); ids.push(s.d.id); if (chosen.length >= 5) break; }
    }
  }
  const reasons = {};
  for (const c of chosen) reasons[c.d.id] = "Relevant documented focus: " + c.d.focus;
  const result = chosen.map((c, i) => ({ id: c.d.id, weight: Math.max(1, Math.min(3, Math.ceil((c.score || 1) / 2) || 1)), reason: reasons[c.d.id] }));
  if (mode === "quick") return result.slice(0, 4);
  if (mode === "consult") return result.slice(0, 1);
  return result;
}
