# BL∞ / BLOK / BL-AEGIS

Index-pilot research package for **BL∞ — Mệnh đề Vô hạn Bách Lâm – Optimizer / Bach Lam Infinity Proposition**.

Version **0.2.0-index-pilot** adds BL-NOVO (novelty ontology), BL-SRS, BL-PIRAL and BL-ICO so every claim can have its own canonical/indexable URL.

This repository is intentionally structured as a living, signed, adversarial, machine-readable epistemic object rather than a single paper.

## Start here

Nếu muốn đường ngắn nhất, đọc `INSTALL_3_STEPS.md` hoặc chạy `python scripts/prepare_release.py --github YOUR_GITHUB_USERNAME --repo bl-infinity --zip`.


1. Read `content/00_README_FIRST.md`.
2. Edit `bl.config.yml`.
3. Push the entire repository to GitHub.
4. Enable GitHub Pages with **GitHub Actions**.
5. Enable **GitHub Discussions**.
6. Optional: install/configure giscus and fill the IDs in `bl.config.yml`.
7. Every push to `main` runs validation, rebuilds the static site, and deploys it.

## Core layers

- `content/` — canonical theory and technical explanation.
- `claims/claims.json` — machine-readable claim registry.
- `critiques/` — critique protocol and response ledger.
- `provenance/` — reasoning lineage, timestamps, origin log, chat-import instructions.
- `machine/` — AI/search/citation manifests, novelty ontology and claim graph.
- generated `site/claims/<ID>/` — one canonical page per claim for indexing/audit.
- generated `site/assets/<CODE>/` — one canonical page per named technology/principle.
- `audit/` — adversarial audit protocol.
- `scripts/` — build and validation tools.
- `site/` — generated static site; do not hand-edit generated pages.

## Epistemic rule

**Global ontological openness is not local logical immunity.**

Every claim must remain attackable at the level that determines its truth-status.
