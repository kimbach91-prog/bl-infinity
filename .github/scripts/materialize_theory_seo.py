#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import html
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://kimbach91-prog.github.io/bl-infinity"
BRAND = ROOT / "assets" / "brand"
OG_SRC = BRAND / "og-src"
OG = BRAND / "og"

PAGES = {
    "research/human-development/index.html": ("cover-human-development", "NGHIÊN CỨU PHÁT TRIỂN CON NGƯỜI", ["NGHIÊN CỨU", "PHÁT TRIỂN", "CON NGƯỜI"]),
    "research/human-development/kevin-nt/index.html": ("cover-kevin-research-studio", "KEVIN RESEARCH STUDIO", ["KEVIN", "RESEARCH", "STUDIO"]),
    "research/human-development/kevin-nt/studio/index.html": ("cover-kevin-research-studio", "KEVIN RESEARCH STUDIO", ["KEVIN", "RESEARCH", "STUDIO"]),
    "research/human-development/kevin-nt/tien-hoa-luong-cuc.html": ("cover-dual-pole", "TIẾN HÓA LƯỠNG CỰC", ["TIẾN HÓA", "LƯỠNG CỰC"]),
    "research/human-development/kevin-nt/attribution-benchmark.html": ("cover-real-application-value", "GIÁ TRỊ ỨNG DỤNG THẬT", ["GIÁ TRỊ", "ỨNG DỤNG", "THẬT"]),
    "books/kevin-intellectual-map/index.html": ("cover-100-works", "BẢN ĐỒ 100 CÔNG TRÌNH GIAO THOA", ["BẢN ĐỒ", "100 CÔNG TRÌNH", "GIAO THOA"]),
}

SEO_BEGIN = "<!-- THEORY-SEO:BEGIN -->"
SEO_END = "<!-- THEORY-SEO:END -->"

REMOVE_PATTERNS = [
    r'<link\s+rel=["\'](?:icon|shortcut icon|apple-touch-icon)["\'][^>]*>\s*',
    r'<meta\s+property=["\']og:image(?::[^"\']+)?["\'][^>]*>\s*',
    r'<meta\s+name=["\']twitter:(?:card|image|image:alt)["\'][^>]*>\s*',
    r'<meta\s+property=["\']og:locale["\'][^>]*>\s*',
    r'<meta\s+name=["\']theme-color["\'][^>]*>\s*',
]


def emblem_svg() -> str:
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="THEORY infinity emblem">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#111a45"/><stop offset="1" stop-color="#6c28ff"/></linearGradient></defs>
<rect width="256" height="256" fill="none"/>
<rect x="48" y="31" width="160" height="25" rx="3" fill="#10183d"/>
<rect x="115" y="48" width="27" height="110" rx="3" fill="#10183d"/>
<path d="M35 161 C65 106 106 103 128 149 C150 195 191 196 221 141 C190 89 150 92 128 149 C106 204 65 205 35 161" fill="none" stroke="url(#g)" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''


def cover_svg(lines: list[str], title: str) -> str:
    n = len(lines)
    if n == 2:
        fs, ys = 92, [330, 448]
    else:
        longest = max(len(x) for x in lines)
        fs = 78 if longest <= 15 else 68
        ys = [300, 395, 490]
    texts = "\n".join(
        f'<text x="70" y="{y}" font-family="DejaVu Serif, Georgia, serif" font-size="{fs}" font-weight="700" fill="#111a33">{escape(line)}</text>'
        for line, y in zip(lines, ys)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="THEORY ∞ — {escape(title)}">
<defs>
  <linearGradient id="brand" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#111a45"/><stop offset="1" stop-color="#6c28ff"/></linearGradient>
</defs>
<rect width="1200" height="630" fill="#f8f4ec"/>
<g transform="translate(70 58) scale(.34)">
  <rect x="0" y="0" width="160" height="24" rx="3" fill="#111a3b"/>
  <rect x="66" y="18" width="28" height="98" rx="3" fill="#111a3b"/>
  <path d="M-10 118 C22 68 58 70 80 113 C102 156 138 158 170 108 C138 63 102 66 80 113 C58 160 22 164 -10 118" fill="none" stroke="url(#brand)" stroke-width="22" stroke-linecap="round"/>
</g>
<line x1="139" y1="58" x2="139" y2="135" stroke="#9b968f" stroke-width="1"/>
<text x="170" y="112" font-family="DejaVu Sans, Arial, sans-serif" font-size="39" letter-spacing="12" fill="#111a33">THEORY</text>
<text x="390" y="111" font-family="DejaVu Sans, Arial, sans-serif" font-size="40" fill="#5b2ad1">∞</text>
<g opacity=".20" fill="none" stroke="#6c42d4" stroke-width="1.4">
  <path d="M675 340 C765 185 890 185 990 340 C1090 495 1215 495 1305 340"/>
  <path d="M675 327 C765 172 890 172 990 327 C1090 482 1215 482 1305 327"/>
  <path d="M675 353 C765 198 890 198 990 353 C1090 508 1215 508 1305 353"/>
  <path d="M700 340 C790 205 890 205 990 340 C1090 475 1190 475 1280 340"/>
  <path d="M650 340 C750 165 890 165 990 340 C1090 515 1230 515 1330 340"/>
</g>
{texts}
</svg>'''


def managed_tags(slug: str, alt: str) -> str:
    img = f"{BASE}/assets/brand/og/{slug}.jpg"
    fav = f"{BASE}/assets/brand/theory-favicon.svg"
    ico = f"{BASE}/assets/brand/favicon.ico"
    apple = f"{BASE}/assets/brand/apple-touch-icon.png"
    safe_alt = html.escape(f"THEORY ∞ — {alt}", quote=True)
    return f'''{SEO_BEGIN}
<link rel="icon" type="image/svg+xml" href="{fav}">
<link rel="shortcut icon" href="{ico}">
<link rel="apple-touch-icon" sizes="180x180" href="{apple}">
<meta name="theme-color" content="#f8f4ec">
<meta property="og:locale" content="vi_VN">
<meta property="og:image" content="{img}">
<meta property="og:image:secure_url" content="{img}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{safe_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{img}">
<meta name="twitter:image:alt" content="{safe_alt}">
{SEO_END}'''


def update_html(path: Path, slug: str, alt: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(re.escape(SEO_BEGIN) + r'.*?' + re.escape(SEO_END), '', text, flags=re.S)
    for pat in REMOVE_PATTERNS:
        text = re.sub(pat, '', text, flags=re.I)
    block = managed_tags(slug, alt)
    if "</head>" not in text.lower():
        raise SystemExit(f"Missing </head>: {path.relative_to(ROOT)}")
    text = re.sub(r'</head>', block + '\n</head>', text, count=1, flags=re.I)
    path.write_text(text, encoding="utf-8")


def write_image_sitemap() -> None:
    rows = []
    for rel, (slug, alt, _) in PAGES.items():
        page = f"{BASE}/{rel}"
        if page.endswith("index.html"):
            page = page[:-10]
        img = f"{BASE}/assets/brand/og/{slug}.jpg"
        rows.append(f'''  <url><loc>{escape(page)}</loc><image:image><image:loc>{escape(img)}</image:loc><image:title>{escape(alt)}</image:title></image:image></url>''')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + '\n'.join(rows) + '\n</urlset>\n'
    (ROOT / "sitemap-images.xml").write_text(xml, encoding="utf-8")


def update_robots() -> None:
    p = ROOT / "robots.txt"
    text = p.read_text(encoding="utf-8") if p.exists() else "User-agent: *\nAllow: /\n"
    line = f"Sitemap: {BASE}/sitemap-images.xml"
    if line not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
    p.write_text(text, encoding="utf-8")


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    OG_SRC.mkdir(parents=True, exist_ok=True)
    OG.mkdir(parents=True, exist_ok=True)
    (BRAND / "theory-favicon.svg").write_text(emblem_svg(), encoding="utf-8")
    for rel, (slug, alt, lines) in PAGES.items():
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"Missing public page: {rel}")
        (OG_SRC / f"{slug}.svg").write_text(cover_svg(lines, alt), encoding="utf-8")
        update_html(path, slug, alt)
    write_image_sitemap()
    update_robots()
    print("THEORY SEO source/materialization metadata: PASS")

if __name__ == "__main__":
    main()
