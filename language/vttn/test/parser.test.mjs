import test from 'node:test';
import assert from 'node:assert/strict';
import { parseConcept, toConceptRecord } from '../runtime/parser.mjs';
import { ConceptRegistry } from '../runtime/concept-registry.mjs';

test('parse Vietnamese concept declaration into stable AST', () => {
  const ast = parseConcept(`khái_niệm vn:logic.nhan_qua "nhân quả" {
  nghĩa: "quan hệ trong đó một biến cố hay điều kiện góp phần tạo nên biến cố hoặc trạng thái khác"
  bí_danh: ["nhân_quả", "gây nên"]
  trạng_thái: draft
  đăng_bộ: formal-vttn
  nguồn: ["prov:demo:logic-001"]
}`);
  assert.equal(ast.conceptId, 'vn:logic.nhan_qua');
  assert.equal(ast.canonicalLabel, 'nhân quả');
  assert.deepEqual(ast.aliases, ['nhân_quả', 'gây nên']);
  assert.equal(ast.status, 'draft');
});

test('unsourced concept is explicitly marked and cannot masquerade as sourced', () => {
  const record = toConceptRecord(parseConcept(`khái_niệm vn:test.chua_nguon "chưa nguồn" {
  nghĩa: "mục thử nghiệm chưa có provenance"
}`));
  assert.deepEqual(record.provenanceRefs, ['UNSOURCED']);
  assert.match(record.notes, /UNSOURCED/u);
});

test('registry resolves Vietnamese aliases and fails on semantic alias collision', () => {
  const registry = new ConceptRegistry();
  const first = toConceptRecord(parseConcept(`khái_niệm vn:logic.nhan_qua "nhân quả" {
  nghĩa: "quan hệ nguyên nhân và kết quả"
  bí_danh: ["nhân_quả"]
  nguồn: ["prov:demo:1"]
}`));
  registry.add(first);
  assert.equal(registry.resolve('NHÂN QUẢ').conceptId, 'vn:logic.nhan_qua');
  assert.equal(registry.resolve('nhân_quả').conceptId, 'vn:logic.nhan_qua');

  assert.throws(() => registry.add({
    conceptId: 'vn:other.collision',
    canonicalLabel: 'nhân_quả',
    aliases: [],
    definition: 'collision test',
    relations: [],
    status: 'draft',
    provenanceRefs: ['prov:demo:2'],
    notes: null
  }), /VTTN_REGISTRY_ALIAS_COLLISION/u);
});
