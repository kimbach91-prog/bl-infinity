const HEADER = /^\s*khái_niệm\s+(vn:[a-z0-9._:-]+)\s+"([^"]+)"\s*\{\s*$/u;
const FIELD = /^\s*([\p{L}_][\p{L}\p{N}_-]*)\s*:\s*(.*?)\s*$/u;

function parseQuoted(value) {
  const match = value.match(/^"([\s\S]*)"$/u);
  if (!match) throw new Error(`VTTN_EXPECTED_QUOTED_STRING:${value}`);
  return match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n');
}

function parseArray(value) {
  if (!value.startsWith('[') || !value.endsWith(']')) throw new Error('VTTN_EXPECTED_ARRAY');
  const body = value.slice(1, -1).trim();
  if (!body) return [];
  const out = [];
  let current = '', quoted = false, escaped = false;
  for (const char of body) {
    if (escaped) { current += char; escaped = false; continue; }
    if (char === '\\') { current += char; escaped = true; continue; }
    if (char === '"') { current += char; quoted = !quoted; continue; }
    if (char === ',' && !quoted) { out.push(parseQuoted(current.trim())); current = ''; continue; }
    current += char;
  }
  if (quoted) throw new Error('VTTN_UNCLOSED_QUOTE');
  if (current.trim()) out.push(parseQuoted(current.trim()));
  return out;
}

function parseScalar(key, raw) {
  if (key === 'bí_danh' || key === 'nguồn') return parseArray(raw);
  if (raw.startsWith('"')) return parseQuoted(raw);
  if (/^(đúng|sai)$/u.test(raw)) return raw === 'đúng';
  if (/^-?\d+(\.\d+)?$/u.test(raw)) return Number(raw);
  return raw;
}

export function parseConcept(source) {
  const lines = String(source).replace(/\r\n/g, '\n').split('\n');
  if (!lines.length) throw new Error('VTTN_EMPTY');
  const header = lines[0].match(HEADER);
  if (!header) throw new Error('VTTN_INVALID_CONCEPT_HEADER');
  const [, conceptId, canonicalLabel] = header;
  const fields = {};
  let closed = false;

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.trim() || line.trim().startsWith('#')) continue;
    if (line.trim() === '}') {
      if (closed) throw new Error('VTTN_MULTIPLE_CLOSE');
      closed = true;
      if (lines.slice(i + 1).some((x) => x.trim() && !x.trim().startsWith('#'))) throw new Error('VTTN_TRAILING_CONTENT');
      break;
    }
    if (closed) throw new Error('VTTN_CONTENT_AFTER_CLOSE');
    const field = line.match(FIELD);
    if (!field) throw new Error(`VTTN_INVALID_FIELD_LINE:${i + 1}`);
    const [, key, raw] = field;
    if (Object.hasOwn(fields, key)) throw new Error(`VTTN_DUPLICATE_FIELD:${key}`);
    fields[key] = parseScalar(key, raw);
  }

  if (!closed) throw new Error('VTTN_UNCLOSED_BLOCK');
  if (typeof fields.nghĩa !== 'string' || !fields.nghĩa.trim()) throw new Error('VTTN_CONCEPT_REQUIRES_MEANING');

  const aliases = Array.isArray(fields.bí_danh) ? fields.bí_danh : [];
  const status = fields.trạng_thái ?? 'draft';
  const allowedStatus = new Set(['draft','reviewed','contested','deprecated','canonical']);
  if (!allowedStatus.has(status)) throw new Error(`VTTN_INVALID_STATUS:${status}`);

  return {
    nodeType: 'ConceptDeclaration',
    conceptId,
    canonicalLabel,
    definition: fields.nghĩa,
    aliases,
    status,
    provenanceRefs: Array.isArray(fields.nguồn) ? fields.nguồn : [],
    register: fields.đăng_bộ ?? 'vi-modern',
    period: fields.thời_kỳ ?? null,
    region: fields.vùng ?? null,
    rawFields: fields
  };
}

export function toConceptRecord(ast) {
  if (!ast || ast.nodeType !== 'ConceptDeclaration') throw new Error('VTTN_EXPECTED_CONCEPT_AST');
  return {
    conceptId: ast.conceptId,
    canonicalLabel: ast.canonicalLabel,
    aliases: [
      { text: ast.canonicalLabel, register: ast.register, period: ast.period, region: ast.region, sourceRef: ast.provenanceRefs[0] ?? null },
      ...ast.aliases.filter((x) => x !== ast.canonicalLabel).map((text) => ({ text, register: ast.register, period: ast.period, region: ast.region, sourceRef: ast.provenanceRefs[0] ?? null }))
    ],
    definition: ast.definition,
    relations: [],
    status: ast.status,
    provenanceRefs: ast.provenanceRefs.length ? ast.provenanceRefs : ['UNSOURCED'],
    notes: ast.provenanceRefs.length ? null : 'Parser inserted UNSOURCED marker; record must not be promoted to canonical without provenance.'
  };
}
