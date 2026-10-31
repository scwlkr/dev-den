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

export function packet(id, brief, root = ROOT) {
  const a = advisor(id, root);
  const briefText = JSON.stringify(brief || {});
  const query = briefText;
  const BUDGET_CHARS = 12000;

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
  let chars = 0;
  const includeSection = (name) => {
    for (const n of rankedNodes) {
      if (n.section !== name) continue;
      if (selectedNodes.includes(n)) continue;
      const c = n.item.text.length;
      if (chars + c > BUDGET_CHARS) continue;
      selectedNodes.push(n);
      chars += c;
    }
  };
  includeSection("_hot");
  includeSection("voice");
  for (const n of rankedNodes) {
    if (selectedNodes.includes(n)) continue;
    const c = n.item.text.length;
    if (chars + c > BUDGET_CHARS) continue;
    selectedNodes.push(n);
    chars += c;
  }

  // Collect supporting evidence ids from selected nodes (full ids retained).
  const neededIds = new Set();
  for (const n of selectedNodes) for (const eid of (n.item.evidence_ids || [])) neededIds.add(eid);
  // Bring passages into packet: all evidence referenced by selected nodes.
  const chosen = a.evidence.filter((e) => neededIds.has(e.id));
  const chosenIds = new Set(chosen.map((e) => e.id));

  // Build knowledge sections from selected nodes, keeping full evidence_ids if all present in chosen; else drop item with note.
  const dropped = [];
  const sectionMap = new Map();
  for (const n of selectedNodes) {
    const ids = n.item.evidence_ids || [];
    const allPresent = ids.every((eid) => chosenIds.has(eid));
    if (!allPresent) { dropped.push(n.item.text.slice(0, 60)); continue; }
    if (!sectionMap.has(n.section)) sectionMap.set(n.section, []);
    sectionMap.get(n.section).push({ text: n.item.text, basis: n.item.basis, evidence_ids: [...ids] });
  }

  const compiledSections = [...sectionMap.entries()].map(([name, items]) => ({ name, items }));

  const voiceItems = sectionMap.get("voice") || [];
  const hotItems = sectionMap.get("_hot") || [];

  const working_context = hotItems.length ? hotItems : (sectionMap.get("_hot") || []);

  const omittedSections = sections.map((s) => s.name).filter((name) => !sectionMap.has(name));

  const result = {
    id: a.id,
    name: a.name,
    focus: a.focus,
    coverage: { works: a.works, words: a.words },
    gaps: a.compiled.gaps,
    working_context,
    voice_guidance: voiceItems,
    knowledge: compiledSections.filter((s) => s.name !== "_hot" && s.name !== "voice"),
    evidence: chosen,
    limits: [...a.compiled.gaps, ...(dropped.length ? ["Dropped claims lacking full support: " + dropped.length] : []), ...(omittedSections.length ? ["Omitted sections due to budget: " + omittedSections.join(", ")] : [])],
    omitted_sections: omittedSections,
  };
  result.fingerprint = hash(JSON.stringify(result));
  return result;
}
export function recommend(brief, root = ROOT, mode = "normal") {
  const text = JSON.stringify(brief).toLowerCase();
  let ids = ["dhh", "tobi", "primeagen", "carmack", "linus"];
  if (/game|graphics|engine|render|latency|performance/.test(text))
    ids = ["carmack", "casey", "blow", "bjarne", "linus"];
  if (/crypto|blockchain|protocol|decentrali/.test(text))
    ids = ["vitalik", "dorsey", "linus", "ritchie", "zuckerberg"];
  if (/architecture|testing|refactor/.test(text))
    ids = ["dhh", "unclebob", "casey", "carmack", "tobi"];
  const reasons = {
    dhh: "Challenge infrastructure and complexity against this team’s product scope.",
    tobi: "Examine tools, developer agency and the shortest path to user value.",
    primeagen:
      "Test learning costs, language ergonomics and the developer workflow.",
    carmack:
      "Demand a working experiment, a maintenance argument and measured results.",
    linus:
      "Stress practical interfaces, compatibility and long-term maintainability.",
    casey: "Challenge abstraction overhead and require performance evidence.",
    blow: "Examine complexity, correctness and whether the tools serve the actual work.",
    bjarne: "Stress resource management, safety and the cost of abstractions.",
    vitalik:
      "Examine protocol assumptions, security and distributed trade-offs.",
    dorsey:
      "Challenge centralization and platform dependencies against product simplicity.",
    ritchie:
      "Examine interface design, portability and implementation constraints.",
    zuckerberg:
      "Examine iteration, ecosystem leverage and scaling assumptions.",
    unclebob:
      "Stress testing, modular boundaries and the cost of future changes.",
  };
  const result = ids.map((id) => ({ id, weight: 1, reason: reasons[id] }));
  if (mode === "quick") return result.slice(0, 4);
  if (mode === "consult") return result.slice(0, 1);
  return result;
}
