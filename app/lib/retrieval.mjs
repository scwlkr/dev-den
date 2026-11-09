export function tokenize(text) {
  const raw = String(text || "");
  const words = [];
  // Preserve camelCase before lowercasing.
  const camelSplit = raw.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
  const lower = camelSplit.toLowerCase();
  // technical identifiers
  for (const chunk of lower.match(/[a-z0-9][a-z0-9_\-+#./]*/g) || []) {
    words.push(chunk);
    for (const part of chunk.split(/[^a-z0-9+#]+/)) {
      if (part) words.push(part);
    }
  }
  // multiword concepts as bigrams from base tokens
  const base = words.filter((w) => w.length >= 2);
  const bigrams = [];
  for (let i = 0; i < base.length - 1; i++) bigrams.push(base[i] + " " + base[i + 1]);
  return [...base, ...bigrams];
  // note: dedup happens in bm25 doc handling? We keep frequencies, so return all tokens including duplicates via array.
}

export function bm25(docs, query, { k1 = 1.5, b = 0.75 } = {}) {
  // docs: array of token arrays (with duplicates for tf)
  const qTokens = tokenize(query);
  const N = docs.length;
  if (!N) return docs.map(() => 0);
  const avgdl = docs.reduce((a, d) => a + d.length, 0) / N || 1;
  const df = new Map();
  for (const d of docs) {
    const seen = new Set(d);
    for (const t of seen) df.set(t, (df.get(t) || 0) + 1);
  }
  return docs.map((d) => {
    const tf = new Map();
    for (const t of d) tf.set(t, (tf.get(t) || 0) + 1);
    let score = 0;
    const dl = d.length || 1;
    for (const t of qTokens) {
      const f = tf.get(t) || 0;
      if (!f) continue;
      const idf = Math.log(1 + (N - (df.get(t) || 0) + 0.5) / ((df.get(t) || 0) + 0.5));
      score += idf * ((f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / avgdl))));
    }
    return score;
  });
}
