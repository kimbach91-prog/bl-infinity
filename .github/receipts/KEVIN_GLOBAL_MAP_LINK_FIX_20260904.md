# Kevin global comparison route fix — 2026-09-04

Status: FIXED_AND_READY_TO_DEPLOY

Root cause: the Kevin Research Studio linked to `../../../../../books/kevin-intellectual-map/`, which climbs one level beyond the `/bl-infinity/` project root on GitHub Pages.

Correct route from `research/human-development/kevin-nt/studio/` is `../../../../books/kevin-intellectual-map/`.

Fix commit: `101cf5c01c2bbf3a9fa6c11c599f0df5b295ff87`.

Audit scope:
- Kevin case root uses `../../../books/kevin-intellectual-map/`.
- Tiến hóa Lưỡng Cực uses `../../../books/kevin-intellectual-map/`.
- Kevin Research Studio uses `../../../../books/kevin-intellectual-map/`.

The underlying global-comparison artifact was never deleted; only the Studio relative URL was wrong.
