# Việt Văn Minh Stack — Roadmap v0.1

## Phase 0 — Foundation (đang thực hiện)

- [x] VTTN semantic language skeleton
- [x] DSFP VTTN payload profile
- [x] nine-platform registry
- [x] provenance schema
- [x] concept schema
- [x] evidence schema
- [x] sovereign snapshot manifest
- [x] foundation integrity checker
- [x] CI leakage/invariant gate
- [x] cultural provenance policy
- [x] open-standard interoperability profile

Exit gate: schema/registry CI xanh; canonical/public/core boundaries rõ.

## Phase 1 — Việt Ngữ + Việt Ký

Mục tiêu: tạo corpus ngôn ngữ và kho lưu trữ có thể sống độc lập.

- parser tối thiểu cho VTTN concept declarations;
- concept resolver + alias register;
- ingestion pipeline cho text/metadata;
- content-addressed artifact store abstraction;
- deterministic snapshot/export;
- TEI import/export adapter candidate;
- archival derivative lineage.

Exit gate: một subset corpus có thể ingest -> canonicalize -> export -> restore offline mà semantic IDs không đổi.

## Phase 2 — Việt Tri Thức + Việt Chứng + Việt Khoa

- claim graph;
- evidence/counterevidence ledger;
- proof status transitions;
- lab/eval record;
- reproducibility package;
- PROV-O export;
- RO-Crate 1.3 export;
- semantic diff round-trip tests.

Exit gate: claim contested không mất phản chứng; experiment có thể tái dựng từ bundle đủ điều kiện.

## Phase 3 — Việt Quyền + Việt Kinh

- capability grammar bằng VTTN;
- consent/delegation/revocation receipts;
- local policy evaluator;
- contribution/cost/compute ledger;
- settlement provenance;
- legal-authority namespace tách khỏi internal policy.

Exit gate: `reachable != authorized` được kiểm chứng bằng test; offline node không tự nâng quyền khi mất coordinator.

## Phase 4 — Việt Học + Việt Văn

- curriculum/competency graph;
- prerequisite resolver;
- assessment evidence;
- cultural graph;
- artifact/claim/interpretation/derivative separation;
- region/period/community facets;
- public reader/editor tools.

Exit gate: người dùng ngoài DEUS có thể học, tra cứu, trích dẫn và đóng góp mà không cần quyền vào core.

## Phase 5 — Sovereign Civilization Node

Một node tối thiểu chứa:

```text
VTTN parser/resolver
concept registry shard
knowledge/evidence shard
policy verifier
archive store
snapshot verifier
DSFP transport adapter
local search/index
public/core disclosure gate
```

Chế độ:
- `FEDERATED_ONLINE`: đồng bộ qua DSFP và adapter mạng được cấp quyền.
- `SOVEREIGN_LOCAL`: hoạt động chỉ với snapshot/local state.
- `AIR_GAPPED`: nhập/xuất qua signed offline bundle.

Exit gate: mất DNS/cloud/relay không làm mất khả năng đọc, kiểm chứng và sử dụng canonical local subset.

## Không được gọi là “hoàn tất” nếu thiếu

- restore drill thật;
- corpus có nguồn thật;
- round-trip interoperability tests;
- independent review cho phần ngữ văn/lịch sử quan trọng;
- security review cho quyền/capability;
- public/core leakage test;
- versioning/migration path.
