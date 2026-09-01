from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

NOVEL_ROBOTS = "noindex,nofollow,noarchive,nosnippet"
DRAFT_ROBOTS = "noindex,follow,max-image-preview:large"
DRAFT_MARKER = "LOCALIZED_DISCOVERY_SUMMARY_AI_DRAFT_UNREVIEWED"


def replace_robots(text: str, value: str) -> str:
    pattern = re.compile(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>', re.I)
    tag = f'<meta name="robots" content="{value}">'
    if pattern.search(text):
        return pattern.sub(tag, text, count=1)
    return text.replace("</head>", tag + "</head>", 1)


def quiet_novel_links(text: str) -> str:
    # Keep the navigation contract structurally present for internal auditing,
    # while removing the fiction entry from the visible public surface.
    def hide_anchor(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r'\bhidden\b', tag, re.I):
            return tag
        return tag[:-1] + ' hidden aria-hidden="true" tabindex="-1" rel="nofollow">'

    text = re.sub(
        r'<a\b(?=[^>]*\bdata-section=["\']novel["\'])[^>]*>',
        hide_anchor,
        text,
        flags=re.I,
    )
    text = re.sub(
        r'<li\b(?=[^>]*\bclass=["\'][^"\']*\bnovel-entry\b[^"\']*["\'])[^>]*>',
        lambda m: m.group(0) if re.search(r'\bhidden\b', m.group(0), re.I) else m.group(0)[:-1] + ' hidden aria-hidden="true">',
        text,
        flags=re.I,
    )
    return text


def canonical_url(text: str) -> str | None:
    match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', text, re.I)
    return match.group(1) if match else None


def main() -> None:
    if not SITE.exists():
        raise SystemExit("site/ does not exist; run build and hardening first")

    noindex_urls: set[str] = set()
    hidden_links = 0
    draft_pages = 0

    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        before = text
        text = quiet_novel_links(text)

        rel = path.relative_to(SITE).as_posix()
        if rel in {"novel/index.html", "novel/chapter-001.html"}:
            text = replace_robots(text, NOVEL_ROBOTS)
            url = canonical_url(text)
            if url:
                noindex_urls.add(url)

        if DRAFT_MARKER in text:
            text = replace_robots(text, DRAFT_ROBOTS)
            draft_pages += 1
            url = canonical_url(text)
            if url:
                noindex_urls.add(url)

        if text != before:
            if 'data-section="novel"' in before or 'class="novel-entry"' in before:
                hidden_links += 1
            path.write_text(text, encoding="utf-8")

    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        # Remove the quiet fiction surface and any unreviewed localized drafts
        # from sitemap submission. They may remain technically reachable while
        # explicitly carrying noindex.
        for url in sorted(noindex_urls):
            text = re.sub(
                r'<url>\s*<loc>' + re.escape(url) + r'</loc>.*?</url>\s*',
                '',
                text,
                flags=re.I | re.S,
            )
        sitemap.write_text(text, encoding="utf-8")

    print(
        f"SEO release guard: hidden fiction links on {hidden_links} pages; "
        f"noindexed {len(noindex_urls)} URLs; localized draft pages={draft_pages}"
    )


if __name__ == "__main__":
    main()
