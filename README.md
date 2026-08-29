# BL∞ / BLOK / BL-AEGIS

Index-pilot research package for **BL∞ — Mệnh đề Vô hạn Bách Lâm – Optimizer / Bach Lam Infinity Proposition**.

Version **0.2.2-bl-adn-publication** publishes the canonical **BL-ADN v0.2.0** protocol alongside **BL-CPR — Công khai Hiến pháp, Bảo vệ Runtime**. The public repository remains a living, signed, adversarial and machine-readable epistemic object; it is not a dump of the private Optimizer production runtime.

## Start here

Nếu muốn đường ngắn nhất, đọc `INSTALL_3_STEPS.md` hoặc chạy `python scripts/prepare_release.py --github YOUR_GITHUB_USERNAME --repo bl-infinity --zip`.

1. Read `content/00_README_FIRST.md`.
2. Read [`BL-ADN.md`](BL-ADN.md) for the canonical lineage/provenance protocol.
3. Read `DISCLOSURE_POLICY.md` before adding technical material.
4. Edit `bl.config.yml`.
5. Push the repository to GitHub.
6. Enable GitHub Pages with **GitHub Actions** and **GitHub Discussions**.
7. Every push to `main` validates the epistemic object and the disclosure boundary before rebuilding/deploying Pages.

## Core public layers

- `BL-ADN.md` — canonical lineage/provenance protocol; published as `bl-adn.html` and raw `bl-adn.md`.
- `content/` — canonical theory and public technical explanation.
- `claims/claims.json` — machine-readable claim registry.
- `critiques/` — critique protocol and response ledger.
- `provenance/` — publishable reasoning lineage, timestamps and source classes.
- `machine/` — AI/search/citation manifests, public ontologies and claim graph.
- generated `site/claims/<ID>/` — one canonical page per claim.
- generated `site/assets/<CODE>/` — one canonical page per named technology/principle.
- `audit/` and `scripts/` — public validation/reference implementation.

## Disclosure boundary

BL∞ publishes what a third party needs to **identify, reconstruct, verify, critique, cite and extend** its public claims. It does not publish production prompts, private routing weights, operator-only diagnostics, credentials, private corpora, raw private conversations, unpatched exploit payloads or influence procedures whose release creates disproportionate misuse risk.

The governing rule is:

> **Public constitution and evidence; protected production runtime.**

See `DISCLOSURE_POLICY.md` and `machine/disclosure-policy.json`. The automated gate is `scripts/disclosure_audit.py`.

## Epistemic rule

**Global ontological openness is not local logical immunity.** Every claim remains attackable at the level that determines its truth-status.

---

**ADN BÁCH LÂM ∞** · `BL-CPR` · origin: Bách Lâm · formalization: AI · status: ADOPTED

