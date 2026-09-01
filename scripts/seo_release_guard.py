from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CANONICAL_BASE = "https://kimbach91-prog.github.io/bl-infinity/"

DRAFT_ROBOTS = "noindex,follow,max-image-preview:large"
DRAFT_MARKER = "LOCALIZED_DISCOVERY_SUMMARY_AI_DRAFT_UNREVIEWED"

# Human-facing canonical entry points that should remain discoverable. The
# novel surface is intentionally public again, but Chapter 1 is explicitly a
# DEMO / NON-CANON artifact; discoverability is not canonization.
CORE_INDEX_ROUTES = (
    "",
    "theory.html",
    "world.html",
    "unknown.html",
    "grand-ending.html",
    "author.html",
    "academic-democracy.html",
    "academic-democracy-technology.html",
    "academic-democracy/discovery.html",
    "bl-adn.html",
    "provenance.html",
    "critique.html",
    "machine.html",
    "languages.html",
    "novel/",
    "novel/chapter-001.html",
    "en/",
    "en/theory.html",
    "author/en/",
)


def replace_robots(text: str, value: str) -> str:
    pattern = re.compile(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>', re.I)
    tag = f'<meta name="robots" content="{value}">'
    if pattern.search(text):
        return pattern.sub(tag, text, count=1)
    return text.replace("</head>", tag + "</head>", 1)


def canonical_url(text: str) -> str | None:
    match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', text, re.I)
    return match.group(1) if match else None


def route_exists(route: str) -> bool:
    if route == "":
        return (SITE / "index.html").exists()
    path = SITE / route
    if route.endswith("/"):
        path = path / "index.html"
    return path.exists()


def ensure_core_sitemap_urls(text: str) -> tuple[str, int]:
    additions: list[str] = []
    for route in CORE_INDEX_ROUTES:
        if not route_exists(route):
            continue
        url = CANONICAL_BASE if route == "" else CANONICAL_BASE + route
        if f"<loc>{url}</loc>" not in text:
            additions.append(
                f"<url><loc>{url}</loc><lastmod>2026-09-01</lastmod></url>"
            )
    if additions:
        text = text.replace("</urlset>", "\n".join(additions) + "\n</urlset>")
    return text, len(additions)


def main() -> None:
    if not SITE.exists():
        raise SystemExit("site/ does not exist; run build and hardening first")

    noindex_urls: set[str] = set()
    draft_pages = 0

    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        before = text

        # Public novel demo pages are deliberately NOT hidden/noindexed here.
        # Canon status is carried by visible labels and machine canon, not by
        # pretending the artifact does not exist.
        if DRAFT_MARKER in text:
            text = replace_robots(text, DRAFT_ROBOTS)
            draft_pages += 1
            url = canonical_url(text)
            if url:
                noindex_urls.add(url)

        if text != before:
            path.write_text(text, encoding="utf-8")

    sitemap = SITE / "sitemap.xml"
    core_added = 0
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        # Unreviewed localized discovery drafts stay out of sitemap.
        for url in sorted(noindex_urls):
            text = re.sub(
                r'<url>\s*<loc>' + re.escape(url) + r'</loc>.*?</url>\s*',
                '',
                text,
                flags=re.I | re.S,
            )
        text, core_added = ensure_core_sitemap_urls(text)
        sitemap.write_text(text, encoding="utf-8")

    print(
        f"SEO release guard: public novel demo unlocked; "
        f"noindexed {len(noindex_urls)} draft URLs; localized draft pages={draft_pages}; "
        f"core sitemap URLs restored={core_added}"
    )


if __name__ == "__main__":
    main()
