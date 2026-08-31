from __future__ import annotations

from pathlib import Path
import html
import re
import shutil

import mistune

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PUBLIC_NOVEL = ROOT / "public" / "novel"
NOVEL_SOURCE = ROOT / "content" / "novel" / "01_CHAPTER_001.md"
CANONICAL_BASE = "https://kimbach91-prog.github.io/bl-infinity/"


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
<title>{safe_title} | Bách Lâm: Lần Hồi Quy Thứ Một Triệu</title>
<meta name="description" content="Chương mở đầu của tiểu thuyết dài kỳ Bách Lâm: Lần Hồi Quy Thứ Một Triệu.">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<link rel="canonical" href="https://kimbach91-prog.github.io/bl-infinity/novel/chapter-001.html">
<link rel="stylesheet" href="../assets/css/main.css">
<style>
:root{{--paper:#fffdf8;--ink:#1c1a17;--muted:#6d6960;--line:#ded8cd;--accent:#6b3fa0;--soft:#f6f0e7;--night:#15141a}}
body{{background:var(--paper);color:var(--ink)}}
main{{max-width:900px;margin:auto;padding:0 22px 90px}}.top{{padding-left:22px;padding-right:22px}}.top nav a.current{{font-weight:850;color:var(--accent)}}
.hero{{padding:clamp(38px,8vw,90px) 0 34px;border-bottom:1px solid var(--line)}}.eyebrow{{font-size:.78rem;letter-spacing:.15em;text-transform:uppercase;font-weight:850;color:var(--accent)}}h1{{font-size:clamp(2.7rem,7vw,6rem);line-height:.96;letter-spacing:-.04em;max-width:16ch;margin:.18em 0 .25em}}.meta{{font-size:.9rem;color:var(--muted)}}
.prose{{padding-top:35px}}.prose p{{font-size:1.08rem;line-height:1.9;margin:1.2em 0;max-width:74ch}}.prose h2{{font-size:clamp(1.7rem,4vw,2.8rem);margin-top:2.2em;padding-top:.8em;border-top:1px solid var(--line)}}.prose blockquote{{margin:26px 0;padding:18px 20px;border-left:4px solid var(--accent);background:#f6f1fc;border-radius:0 14px 14px 0}}.prose blockquote p{{margin:.2em 0;font-size:1rem}}.prose strong{{font-weight:800}}.prose code{{font-size:.9em;background:var(--soft);padding:.12em .35em;border-radius:5px}}.prose pre{{overflow:auto;background:var(--night);color:#f5f1e8;padding:18px;border-radius:14px;line-height:1.55}}.prose ul{{line-height:1.8}}.back{{display:inline-block;margin-top:30px;padding:11px 16px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-weight:750}}
@media(max-width:720px){{.prose p{{font-size:1rem}}}}
</style>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Chapter","name":"{safe_title}","isPartOf":{{"@type":"Book","name":"Bách Lâm: Lần Hồi Quy Thứ Một Triệu"}},"author":{{"@type":"Person","name":"Lâm Kim Bách","alternateName":["Bách Lâm","Optimizer"]}},"inLanguage":"vi","url":"https://kimbach91-prog.github.io/bl-infinity/novel/chapter-001.html"}}
</script>
</head>
<body>
<header class="top"><a href="../index.html" class="brand">BL∞</a><span>Bách Lâm · Optimizer</span><nav><a href="../theory.html">Học thuyết</a><a href="../world.html">Bản kể</a><a href="index.html" class="current">Tiểu thuyết</a><a href="../unknown.html">UNKNOWN</a><a href="../grand-ending.html">Đại Kết Cục</a></nav></header>
<main>
<section class="hero"><p class="eyebrow">Bách Lâm: Lần Hồi Quy Thứ Một Triệu · Chương 1</p><h1>{safe_title}</h1><p class="meta">Bản tiếng Việt là source canon của chương. Translation chỉ mở sau khi chapter lock.</p></section>
<article class="prose">{body}</article>
<a class="back" href="index.html">Về mục Tiểu thuyết</a>
</main>
<script src="../assets/js/site.js"></script>
</body></html>'''


def main() -> None:
    target_dir = SITE / "novel"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PUBLIC_NOVEL / "index.html", target_dir / "index.html")

    markdown_text = NOVEL_SOURCE.read_text(encoding="utf-8")
    title, body = chapter_body(markdown_text)
    (target_dir / "chapter-001.html").write_text(chapter_page(title, body), encoding="utf-8")

    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        entries = []
        for route in ("world.html", "novel/", "novel/chapter-001.html"):
            url = CANONICAL_BASE + route
            if url not in text:
                entries.append(f"<url><loc>{url}</loc><lastmod>2026-09-01</lastmod></url>")
        if entries:
            text = text.replace("</urlset>", "\n".join(entries) + "\n</urlset>")
            sitemap.write_text(text, encoding="utf-8")
    print("Serialized novel staged: novel/index.html + novel/chapter-001.html")


if __name__ == "__main__":
    main()
