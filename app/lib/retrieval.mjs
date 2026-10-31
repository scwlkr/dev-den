// Retrieval helpers shared by knowledge packeting and evidence search.
export function tokenize(text) {
  const s = String(text || "").toLowerCase();
  const words = [];
  // technical identifiers: split camelCase and keep original
  for (const chunk of s.match(/[a-z0-9][a-z0-9_\-./]*/g) || []) {
    words.push(chunk);
    for (const part of chunk.split(/[^a-z0-9]+/)) {
      if (part) words.push(part);
    }
    // camelCase split
    for (const part of chunk.replace(/([a-z])([A-Z])/g, "$1 $2").split(/\s+/)) {
      if (part && part !== chunk) words.push(part.toLowerCase());
    }
  }
  // multiword concepts as bigrams
  const base = words.filter((w) => w.length >= 2);
  const bigrams = [];
  for (let i = 0; i < base.length - 1; i++) bigrams.push(base[i] + " " + base[i + 1]);
  return [...new Set([...base, ...bigrams])];
}

export function bm25(docs, query, { k1 = 1.5, b = 0.75 } = {}) {
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
