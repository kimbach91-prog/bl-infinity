# THEORY SEO release receipt — 2026-09-04

Final canonical materialized source commit: `8faf71e878a2066b02361e12b7b433d6ec33f123`.

Public asset family is intentionally routed through the already-curated `books/` Pages allowlist:

- `books/theory-assets/theory-favicon.svg`
- `books/theory-assets/favicon.ico`
- `books/theory-assets/apple-touch-icon.png`
- `books/theory-assets/og/cover-human-development.jpg`
- `books/theory-assets/og/cover-kevin-research-studio.jpg`
- `books/theory-assets/og/cover-dual-pole.jpg`
- `books/theory-assets/og/cover-100-works.jpg`
- `books/theory-assets/og/cover-real-application-value.jpg`

Final gates passed before promotion:

- vector THEORY favicon and cover source generation;
- crawler-safe JPEG rendering at exactly 1200×630;
- Apple touch icon 180×180 and multi-size ICO fallback;
- one canonical `og:image` per target page;
- `og:image` secure URL, type, dimensions and alt text;
- `twitter:card=summary_large_image` and matching image/alt;
- `og:locale=vi_VN`, `og:site_name=THEORY ∞` and theme color;
- canonical URL retained;
- `max-image-preview:large` retained/added;
- image entries integrated into the existing public sitemap;
- title length gate ≤60 characters and description length gate ≤160 characters;
- asset weight ceilings and `git diff --check`.

Rendered final weights at the first complete audit were approximately 34–45 KB per 1200×630 cover, 667 bytes for the SVG favicon, 7 KB for the Apple icon and 15 KB for the multi-size ICO.

This receipt contains no secrets and is not copied into the curated Pages artifact.