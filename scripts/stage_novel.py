from __future__ import annotations

from pathlib import Path
import html
import json
import re
import shutil

import mistune

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PUBLIC_NOVEL = ROOT / "public" / "novel"
PUBLIC_ROOT = ROOT / "public"
NOVEL_SOURCE = ROOT / "content" / "novel" / "01_CHAPTER_001.md"
MACHINE = ROOT / "machine"
CANONICAL_BASE = "https://kimbach91-prog.github.io/bl-infinity/"
LASTMOD = "2026-09-02"


def chapter_body(markdown_text: str) -> tuple[str, str]:
    title_match = re.search(r"^#\s+(.+)$", markdown_text, flags=re.M)
    title = title_match.group(1).strip() if title_match else "Chương 1"
    body_source = re.sub(r"^#\s+.+?\n+", "", markdown_text, count=1, flags=re.M)
    renderer = mistune.create_markdown(escape=False)
    return title, renderer(body_source)


def chapter_page(title: str, body: str) -> str:
    safe_title = html.escape(title)
    return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title} | HALF-CANON · Tiểu thuyết BL∞</title>
<meta name="description" content="Chương 1 HALF-CANON của Bách Lâm: Lần Hồi Quy Thứ Một Triệu. Locked core, world build neo vào Việt Nam đầu thế kỷ XXI và các cơ chế sâu vẫn giữ UNKNOWN khi chưa đủ căn cứ.">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="https://kimbach91-prog.github.io/bl-infinity/novel/chapter-001.html">
<link rel="stylesheet" href="../assets/css/main.css">
<style>
:root{{--paper:#fffdf8;--ink:#1c1a17;--muted:#6d6960;--line:#ded8cd;--accent:#6b3fa0;--soft:#f6f0e7;--night:#15141a}}
html{{-webkit-text-size-adjust:100%;text-size-adjust:100%}}body{{background:var(--paper);color:var(--ink)}}
main{{max-width:860px;margin:auto;padding:0 22px 86px}}.top{{padding-left:22px;padding-right:22px}}.hero{{padding:clamp(34px,7vw,78px) 0 30px;border-bottom:1px solid var(--line)}}.eyebrow{{font-size:.76rem;letter-spacing:.14em;text-transform:uppercase;font-weight:850;color:var(--accent)}}h1{{font-size:clamp(2.55rem,6.5vw,5.6rem);line-height:.97;letter-spacing:-.04em;max-width:16ch;margin:.18em 0 .22em}}.meta{{font-size:.9rem;color:var(--muted)}}
.canon-note{{margin:22px 0 0;padding:15px 17px;border:1px solid #ddcfaa;border-radius:14px;background:#fff8e6;font-size:.95rem;line-height:1.65;max-width:72ch}}.prose{{padding-top:28px}}.prose p{{font-size:1.04rem;line-height:1.78;margin:.78em 0;max-width:70ch;text-wrap:pretty}}.prose p+p{{margin-top:.72em}}.prose h2,.prose h3{{margin-top:2.2em;padding-top:.7em;border-top:1px solid var(--line)}}.prose blockquote{{margin:20px 0;padding:15px 18px;border-left:4px solid var(--accent);background:#f6f1fc;border-radius:0 14px 14px 0}}.prose blockquote p{{margin:.15em 0;font-size:.96rem;line-height:1.65}}.prose hr{{border:0;border-top:1px solid var(--line);margin:2.15em 0}}.prose strong{{font-weight:800}}.prose code{{font-size:.9em;background:var(--soft);padding:.12em .35em;border-radius:5px}}.prose pre{{overflow:auto;background:var(--night);color:#f5f1e8;padding:18px;border-radius:14px;line-height:1.55}}.prose ul{{line-height:1.75}}.back{{display:inline-block;margin-top:30px;margin-right:8px;padding:11px 16px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-weight:750}}
@media(max-width:720px){{main{{padding:0 18px 72px}}.hero{{padding:30px 0 24px}}.prose{{padding-top:22px}}.prose p{{font-size:1rem;line-height:1.72;margin:.65em 0}}.prose p+p{{margin-top:.58em}}.prose blockquote{{margin:16px 0;padding:13px 15px}}.prose hr{{margin:1.75em 0}}}}
</style>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Chapter","name":"{safe_title}","isPartOf":{{"@type":"Book","name":"Bách Lâm: Lần Hồi Quy Thứ Một Triệu"}},"author":{{"@type":"Person","name":"Lâm Kim Bách","alternateName":["Bách Lâm","Optimizer"]}},"dateModified":"2026-09-02","inLanguage":"vi","url":"https://kimbach91-prog.github.io/bl-infinity/novel/chapter-001.html","description":"Public HALF-CANON v1. Core events bind future dependencies; sourced real-world anchors bind where stated; scene texture remains patchable and deep mechanisms may remain UNKNOWN."}}</script>
</head>
<body>
<header class="top"><a href="../index.html" class="brand">BL∞</a><span>Bách Lâm · Optimizer</span><nav><a href="../theory.html">Học thuyết</a><a href="../system.html">Hệ Bảo Toàn</a><a href="index.html">Tiểu thuyết</a><a href="world-chapter-001.html">World Ch.1</a><a href="../unknown.html">UNKNOWN</a></nav></header>
<main>
<section class="hero"><p class="eyebrow">PUBLIC HALF-CANON v1 · Chương 1</p><h1>{safe_title}</h1><p class="meta">Lâm Kim Bách · Bách Lâm / Optimizer</p><div class="canon-note"><strong>Continuity:</strong> <code>LockedCore + RealityAnchors + OpenGaps</code>. HALF-CANON không phải 50% xác suất đúng. Sự kiện lõi của chương tạo dependency; neo lịch sử–xã hội có nguồn; cơ chế sâu chưa đủ căn cứ vẫn được phép giữ UNKNOWN. Fiction không tự trở thành science hoặc autobiography.</div></section>
<article class="prose">{body}</article>
<a class="back" href="index.html">Về mục Tiểu thuyết</a><a class="back" href="world-chapter-001.html">World / Reality Anchors</a>
</main>
<script src="../assets/js/site.js"></script>
</body></html>'''


def append_sitemap(routes: tuple[str, ...]) -> None:
    sitemap = SITE / "sitemap.xml"
    if not sitemap.exists():
        return
    text = sitemap.read_text(encoding="utf-8")
    for route in routes:
        url = CANONICAL_BASE + route
        if f"<loc>{url}</loc>" not in text:
            text = text.replace(
                "</urlset>",
                f"<url><loc>{url}</loc><lastmod>{LASTMOD}</lastmod></url>\n</urlset>",
            )
    sitemap.write_text(text, encoding="utf-8")


def enrich_manifest() -> None:
    manifest_path = SITE / "machine" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["conservation_system"] = "bl-conservation-system.json"
    manifest["open_academic_publishing"] = "open-academic-publishing.json"
    manifest["novel_public_canon"] = "novel-canon.json"
    manifest["chapter_001_reality_anchors"] = "chapter-001-reality-anchors.json"
    manifest["novel_half_canon_page"] = "../novel/chapter-001.html"
    manifest["chapter_001_world_guide"] = "../novel/world-chapter-001.html"
    manifest["system_hub"] = "../system.html"
    manifest["open_academic_publishing_page"] = "../open-academic-publishing.html"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    target_dir = SITE / "novel"
    target_dir.mkdir(parents=True, exist_ok=True)
    (SITE / "machine").mkdir(parents=True, exist_ok=True)

    shutil.copyfile(PUBLIC_NOVEL / "index.html", target_dir / "index.html")
    shutil.copyfile(PUBLIC_NOVEL / "world-chapter-001.html", target_dir / "world-chapter-001.html")
    shutil.copyfile(PUBLIC_ROOT / "system.html", SITE / "system.html")
    shutil.copyfile(PUBLIC_ROOT / "open-academic-publishing.html", SITE / "open-academic-publishing.html")

    for name in (
        "novel-canon.json",
        "chapter-001-reality-anchors.json",
        "bl-conservation-system.json",
        "open-academic-publishing.json",
    ):
        shutil.copyfile(MACHINE / name, SITE / "machine" / name)

    markdown_text = NOVEL_SOURCE.read_text(encoding="utf-8")
    title, body = chapter_body(markdown_text)
    (target_dir / "chapter-001.html").write_text(chapter_page(title, body), encoding="utf-8")

    enrich_manifest()
    append_sitemap((
        "novel/",
        "novel/chapter-001.html",
        "novel/world-chapter-001.html",
        "system.html",
        "open-academic-publishing.html",
    ))
    print("Serialized novel HALF-CANON + reality world guide + BL conservation/publication surfaces staged")


if __name__ == "__main__":
    main()
