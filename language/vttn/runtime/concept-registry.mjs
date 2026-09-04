function norm(text) {
  return String(text).normalize('NFC').trim().toLocaleLowerCase('vi-VN').replace(/\s+/g, ' ');
}

export class ConceptRegistry {
  #byId = new Map();
  #aliasToId = new Map();

  add(record) {
    if (!record?.conceptId) throw new Error('VTTN_REGISTRY_CONCEPT_ID_REQUIRED');
    if (this.#byId.has(record.conceptId)) throw new Error(`VTTN_REGISTRY_DUPLICATE_ID:${record.conceptId}`);
    const aliases = Array.isArray(record.aliases) ? record.aliases.map((x) => x.text) : [];
    const labels = [record.canonicalLabel, ...aliases].filter(Boolean);

    for (const label of labels) {
      const key = norm(label);
      const existing = this.#aliasToId.get(key);
      if (existing && existing !== record.conceptId) throw new Error(`VTTN_REGISTRY_ALIAS_COLLISION:${label}:${existing}:${record.conceptId}`);
    }

    const frozen = structuredClone(record);
    this.#byId.set(record.conceptId, frozen);
    for (const label of labels) this.#aliasToId.set(norm(label), record.conceptId);
    return structuredClone(frozen);
  }

  get(conceptId) {
    const record = this.#byId.get(conceptId);
    return record ? structuredClone(record) : null;
  }

  resolve(labelOrId) {
    if (this.#byId.has(labelOrId)) return this.get(labelOrId);
    const id = this.#aliasToId.get(norm(labelOrId));
    return id ? this.get(id) : null;
  }

  list() {
    return [...this.#byId.values()].map((x) => structuredClone(x));
  }

  stats() {
    return { concepts: this.#byId.size, aliases: this.#aliasToId.size };
  }
}
