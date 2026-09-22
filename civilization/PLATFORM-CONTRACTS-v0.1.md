# Platform Contracts v0.1

Mỗi nền tảng phải cung cấp cùng bốn cổng tối thiểu:

```text
PUT record      -> validate -> canonical candidate
GET record      -> disclosure gate -> canonical view
EXPORT snapshot -> deterministic manifest + hashes
VERIFY snapshot -> offline integrity + semantic compatibility
```

Không nền tảng nào được dùng DNS, cloud account hoặc vendor ID làm canonical identity.

## VNG — Việt Ngữ

Input: từ/cụm từ, register, thời kỳ, vùng, nguồn, định nghĩa, alias.
Output: `ConceptRecord` + VTTN concept ID.
Gate: từ lịch sử/phương ngữ không có nguồn phải `UNSOURCED` hoặc `draft`, không canonical hóa tự động.
Offline: full lexicon shard + concept graph + hashes.

## VKT — Việt Tri Thức

Input: claim, source refs, evidence refs, temporal scope.
Output: claim node với trạng thái `supported / contested / unknown / normative / hypothesis`.
Gate: không biến consensus cục bộ thành fact toàn cục; counterevidence phải giữ lại.
Offline: knowledge subgraph theo scope + evidence links.

## VC — Việt Chứng

Input: claimRef + EvidenceRecord.
Output: evidence ledger và proof status.
Gate: formal proof, empirical evidence và philosophical argument là ba lớp khác nhau; không cộng điểm mù để tạo “certainty”.
Offline: proof/evidence bundle + verifier metadata.

## VQ — Việt Quyền

Input: subject, capability, scope, grantor, expiry, revocation conditions, authority provenance.
Output: signed/revocable capability record.
Gate: `reachable != authorized`; luật mô tả, luật hiện hành và chính sách nội bộ phải tách namespace.
Offline: local policy cache chỉ có hiệu lực trong phạm vi đã ký; revoke list đi kèm snapshot.

## VHOC — Việt Học

Input: competency, prerequisite graph, sources, assessment/eval.
Output: curriculum path và proof-of-competency record.
Gate: không đồng nhất “đã đọc” với “đã hiểu”; milestone phải có kiểm chứng.
Offline: curriculum shard + nguồn đã cache + bài kiểm tra có checksum.

## VKY — Việt Ký

Input: artifact + metadata + rights + provenance.
Output: immutable archive object + derivatives có lineage.
Gate: bản số hóa, bản phục dựng, bản dịch và bản diễn giải phải là artifact khác nhau.
Offline: content-addressed bundle + manifest + restore guide.

## VKHOA — Việt Khoa

Input: hypothesis, method, data, code/software refs, environment, result.
Output: experiment/eval record + reproducibility bundle.
Gate: negative result và failed replication không bị xóa; observation != interpretation.
Offline: RO-Crate-compatible research package + sovereign root hash.

## VKINH — Việt Kinh

Input: contribution, cost, compute, settlement basis, contract/consent refs.
Output: auditable value/contribution entry.
Gate: credit nội bộ không được mô tả thành tiền/chứng khoán/quyền sở hữu nếu pháp lý không hỗ trợ.
Offline: signed accounting journal + replay-safe IDs.

## VVAN — Việt Văn

Input: tác phẩm/biểu tượng/nghi lễ/thể loại/diễn giải + source/region/period/community.
Output: cultural graph record + interpretation layers.
Gate: tách `artifact`, `historical claim`, `interpretation`, `creative derivative`.
Offline: heritage shard + text/image/audio derivatives + provenance manifest.

## Common response envelope

```json
{
  "recordId": "...",
  "canonicalVersion": 1,
  "conceptIds": [],
  "epistemicClass": "OBS|INFER|ASSUME|NORM|HYPOTHESIS|UNSOURCED",
  "disclosureClass": "PUBLIC|COMMON|RESTRICTED|BLACK_CORE",
  "provenanceRefs": [],
  "evidenceRefs": [],
  "contentHash": "sha256:...",
  "status": "candidate|canonical|contested|deprecated"
}
```

## Cross-platform invariant

Không có nền tảng nào được tự ý nâng:

```text
UNSOURCED -> OBS
HYPOTHESIS -> supported
RESTRICTED -> COMMON
COMMON -> PUBLIC
candidate -> canonical
```

Mọi nâng hạng cần một transition record có actor, authority, evidence, timestamp và hash.
