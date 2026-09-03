import { sha256Json } from './canonical.mjs';
const WORD_RE = /[\p{L}\p{N}_]+/gu;
export function tokenize(text) { return String(text ?? '').toLocaleLowerCase().match(WORD_RE) ?? []; }
function hashedVector(tokens, dims = 128) { const vector = new Float64Array(dims); for (const token of tokens) { let h = 2166136261; for (let i = 0; i < token.length; i += 1) { h ^= token.charCodeAt(i); h = Math.imul(h, 16777619); } vector[Math.abs(h) % dims] += 1; } const norm = Math.hypot(...vector) || 1; for (let i = 0; i < vector.length; i += 1) vector[i] /= norm; return vector; }
function cosine(a, b) { let dot = 0; for (let i = 0; i < Math.min(a.length, b.length); i += 1) dot += a[i] * b[i]; return dot; }
export class HybridSearchFabric {
  constructor({ vectorDims = 128 } = {}) { this.vectorDims = vectorDims; this.docs = new Map(); this.df = new Map(); this.totalLength = 0; this.graph = new Map(); }
  addDocument(doc) {
    validateDoc(doc); if (this.docs.has(doc.id)) this.removeDocument(doc.id);
    const tokens = tokenize(`${doc.title ?? ''} ${doc.text ?? ''}`), tf = new Map(); for (const token of tokens) tf.set(token, (tf.get(token) ?? 0) + 1); for (const token of tf.keys()) this.df.set(token, (this.df.get(token) ?? 0) + 1); this.totalLength += tokens.length;
    const stored = { ...structuredClone(doc), tokens, tf, vector: hashedVector(tokens, this.vectorDims), trust: clamp01(doc.trust ?? 0.5), contentHash: sha256Json({ title: doc.title ?? '', text: doc.text ?? '', source: doc.source ?? null }) };
    this.docs.set(doc.id, stored); for (const rel of doc.relations ?? []) { if (!this.graph.has(doc.id)) this.graph.set(doc.id, new Map()); this.graph.get(doc.id).set(rel.target, Number(rel.weight ?? 1)); } return publicDoc(stored);
  }
  removeDocument(id) { const old = this.docs.get(id); if (!old) return false; for (const token of old.tf.keys()) { const next = (this.df.get(token) ?? 1) - 1; if (next <= 0) this.df.delete(token); else this.df.set(token, next); } this.totalLength -= old.tokens.length; this.docs.delete(id); this.graph.delete(id); for (const edges of this.graph.values()) edges.delete(id); return true; }
  search(query, { limit = 10, seedIds = [], lexicalWeight = 0.5, semanticWeight = 0.3, graphWeight = 0.1, trustWeight = 0.1, freshnessHalfLifeDays = 365 } = {}) {
    const qTokens = tokenize(query), qVector = hashedVector(qTokens, this.vectorDims), graphBoost = this.#graphBoost(seedIds), avgdl = this.docs.size ? this.totalLength / this.docs.size : 1, now = Date.now(), results = [];
    for (const doc of this.docs.values()) { const lexical = bm25(qTokens, doc, this.df, this.docs.size, avgdl), semantic = cosine(qVector, doc.vector), graph = graphBoost.get(doc.id) ?? 0, freshness = freshnessScore(doc.updatedAt ?? doc.createdAt, now, freshnessHalfLifeDays), trust = doc.trust; const total = lexicalWeight * normalizeLexical(lexical) + semanticWeight * semantic + graphWeight * graph + trustWeight * trust; results.push({ id: doc.id, title: doc.title ?? null, source: doc.source ?? null, score: Number((total * freshness).toFixed(6)), trust, updatedAt: doc.updatedAt ?? null, contentHash: doc.contentHash, explain: { lexical: Number(lexical.toFixed(6)), semantic: Number(semantic.toFixed(6)), graph: Number(graph.toFixed(6)), freshness: Number(freshness.toFixed(6)) } }); }
    return results.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, Math.max(1, limit));
  }
  stats() { return { documents: this.docs.size, vocabulary: this.df.size, relations: [...this.graph.values()].reduce((n, m) => n + m.size, 0) }; }
  #graphBoost(seedIds) { const scores = new Map(); for (const seed of seedIds) { scores.set(seed, Math.max(scores.get(seed) ?? 0, 1)); for (const [target, weight] of this.graph.get(seed) ?? []) scores.set(target, Math.max(scores.get(target) ?? 0, Math.min(1, weight))); } return scores; }
}
function bm25(queryTokens, doc, df, nDocs, avgdl, k1 = 1.2, b = 0.75) { let score = 0; for (const term of new Set(queryTokens)) { const freq = doc.tf.get(term) ?? 0; if (!freq) continue; const dfi = df.get(term) ?? 0, idf = Math.log(1 + (nDocs - dfi + 0.5) / (dfi + 0.5)), denom = freq + k1 * (1 - b + b * doc.tokens.length / Math.max(1, avgdl)); score += idf * (freq * (k1 + 1)) / denom; } return score; }
function normalizeLexical(score) { return score <= 0 ? 0 : score / (1 + score); }
function clamp01(x) { return Math.max(0, Math.min(1, Number(x))); }
function freshnessScore(date, now, halfLifeDays) { if (!date) return 1; const ts = Date.parse(date); if (!Number.isFinite(ts)) return 1; return Math.pow(0.5, Math.max(0, now - ts) / 86_400_000 / Math.max(1, halfLifeDays)); }
function validateDoc(doc) { if (!doc?.id) throw new Error('document.id is required'); if (!doc.text && !doc.title) throw new Error('document text or title is required'); }
function publicDoc(doc) { const { tokens: _tokens, tf: _tf, vector: _vector, ...out } = doc; return structuredClone(out); }
