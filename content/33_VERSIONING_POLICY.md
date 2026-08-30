# 33 — Versioning policy

BL∞ dùng semantic-like versioning cho research object.

## v0.x — Origin / preformal stage

Allowed:

- rename claims;
- restructure axioms;
- reject major parts;
- add exact transcript provenance;
- change technical architecture.

## v1.0 — First canonical public edition

Điều kiện đề xuất:

- exact raw origin transcript imported or sealed+hashed;
- core claims have IDs/types/dependencies;
- prior-art seed map audited at least once;
- static site live;
- Discussions enabled;
- canonical URL stable;
- signed/tagged release;
- mathematical claims reviewed beyond LLM-only pass.

## Patch v1.0.x

Typos, links, metadata, formatting; không đổi semantic claim đáng kể.

## Minor v1.x

Add new claims/proofs/evidence without breaking core definitions; changelog required.

## Major v2.x

Breaking ontology/axiom changes, rejected core premises or major rearchitecture.

## Never rewrite releases

Published release artifacts should remain accessible. Correction produces new version with explicit relation.
