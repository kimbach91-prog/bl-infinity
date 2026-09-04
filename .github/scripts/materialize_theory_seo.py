#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import html
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://kimbach91-prog.github.io/bl-infinity"
PUBLIC_ASSET_PATH = "books/theory-assets"
ASSET_BASE = f"{BASE}/{PUBLIC_ASSET_PATH}"
BRAND = ROOT / PUBLIC_ASSET_PATH
OG_SRC = BRAND / "og-src"
OG = BRAND / "og"

# rel: slug, cover title, cover lines, SEO title, SEO description
PAGES = {
    "research/human-development/index.html": (
        "cover-human-development", "NGHIÊN CỨU PHÁT TRIỂN CON NGƯỜI", ["NGHIÊN CỨU", "PHÁT TRIỂN", "CON NGƯỜI"],
        "Nghiên cứu phát triển con người | Bách Lâm ∞",
        "Công trình nghiên cứu phát triển con người của Bách Lâm: quan sát, phản biện hai chiều, thử nghiệm và tăng năng lực bằng bằng chứng."
    ),
    "research/human-development/kevin-nt/index.html": (
        "cover-kevin-research-studio", "KEVIN RESEARCH STUDIO", ["KEVIN", "RESEARCH", "STUDIO"],
        "Kevin T.N: nghiên cứu phát triển con người | Bách Lâm",
        "Case study Kevin T.N trong chương trình phát triển con người của Bách Lâm: năng lực, phản biện, thử nghiệm, Reality Veto và đồng phát triển."
    ),
    "research/human-development/kevin-nt/studio/index.html": (
        "cover-kevin-research-studio", "KEVIN RESEARCH STUDIO", ["KEVIN", "RESEARCH", "STUDIO"],
        "Kevin Research Studio | Bách Lâm ↔ Kevin T.N",
        "Giao diện nghiên cứu hai chiều giữa Bách Lâm và Kevin T.N: đọc nghiên cứu, phản biện claim, xem benchmark và cùng sửa mô hình bằng nguồn."
    ),
    "research/human-development/kevin-nt/tien-hoa-luong-cuc.html": (
        "cover-dual-pole", "TIẾN HÓA LƯỠNG CỰC", ["TIẾN HÓA", "LƯỠNG CỰC"],
        "Tiến hóa Lưỡng Cực | Bách Lâm ↔ Kevin T.N",
        "Hồ sơ nguồn về Tiến hóa Lưỡng Cực giữa Bách Lâm và Kevin T.N: tranh luận hai chiều, attribution, phép thử và cơ chế cùng sửa mô hình."
    ),
    "research/human-development/kevin-nt/attribution-benchmark.html": (
        "cover-real-application-value", "GIÁ TRỊ ỨNG DỤNG THẬT", ["GIÁ TRỊ", "ỨNG DỤNG", "THẬT"],
        "Giá trị ứng dụng thật | Bách Lâm ↔ Kevin T.N",
        "Quy tắc phân loại nguồn gốc và benchmark giá trị ứng dụng thật giữa Bách Lâm và Kevin T.N, giữ hệ gốc Kevin độc lập và attribution rõ."
    ),
    "books/kevin-intellectual-map/index.html": (
        "cover-100-works", "BẢN ĐỒ 100 CÔNG TRÌNH GIAO THOA", ["BẢN ĐỒ", "100 CÔNG TRÌNH", "GIAO THOA"],
        "Kevin T.N: Bản đồ 100 công trình giao thoa",
        "Bản đồ 100 công trình giao thoa dành cho Kevin T.N: prior art, candidate novel delta, lộ trình phát triển và trình đọc dài bằng tiếng Việt."
    ),
}

SEO_BEGIN = "<!-- THEORY-SEO:BEGIN -->"
SEO_END = "<!-- THEORY-SEO:END -->"

REMOVE_PATTERNS = [
    r'<link\s+rel=["\'](?:icon|shortcut icon|apple-touch-icon)["\'][^>]*>\s*',
    r'<meta\s+property=["\']og:image(?::[^"\']+)?["\'][^>]*>\s*',
    r'<meta\s+property=["\']og:locale["\'][^>]*>\s*',
    r'<meta\s+property=["\']og:site_name["\'][^>]*>\s*',
    r'<meta\s+name=["\']twitter:(?:card|image|image:alt)["\'][^>]*>\s*',
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
    if len(lines) == 2:
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
<defs><linearGradient id="brand" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#111a45"/><stop offset="1" stop-color="#6c28ff"/></linearGradient></defs>
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
    img = f"{ASSET_BASE}/og/{slug}.jpg"
    fav = f"{ASSET_BASE}/theory-favicon.svg"
    ico = f"{ASSET_BASE}/favicon.ico"
    apple = f"{ASSET_BASE}/apple-touch-icon.png"
    safe_alt = html.escape(f"THEORY ∞ — {alt}", quote=True)
    return f'''{SEO_BEGIN}
<link rel="icon" type="image/svg+xml" href="{fav}">
<link rel="shortcut icon" href="{ico}">
<link rel="apple-touch-icon" sizes="180x180" href="{apple}">
<meta name="theme-color" content="#f8f4ec">
<meta property="og:locale" content="vi_VN">
<meta property="og:site_name" content="THEORY ∞">
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


def set_meta_content(text: str, key_type: str, key: str, value: str) -> str:
    pat = re.compile(r'<meta\s+' + re.escape(key_type) + r'=["\']' + re.escape(key) + r'["\'][^>]*content=["\'][^"\']*["\'][^>]*>', re.I)
    replacement = f'<meta {key_type}="{key}" content="{html.escape(value, quote=True)}">'
    return pat.sub(replacement, text, count=1) if pat.search(text) else text


def ensure_large_image_robot(text: str) -> str:
    m = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']*)["\'][^>]*>', text, re.I)
    if not m:
        return text
    directives = [x.strip() for x in m.group(1).split(',') if x.strip()]
    if not any(x.lower().startswith('max-image-preview:') for x in directives):
        directives.append('max-image-preview:large')
    replacement = f'<meta name="robots" content="{html.escape(",".join(directives), quote=True)}">'
    return text[:m.start()] + replacement + text[m.end():]


def update_html(path: Path, slug: str, alt: str, seo_title: str, seo_desc: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(re.escape(SEO_BEGIN) + r'.*?' + re.escape(SEO_END), '', text, flags=re.S)
    for pat in REMOVE_PATTERNS:
        text = re.sub(pat, '', text, flags=re.I)
    text = re.sub(r'<title>.*?</title>', f'<title>{html.escape(seo_title)}</title>', text, count=1, flags=re.I | re.S)
    text = set_meta_content(text, 'name', 'description', seo_desc)
    text = set_meta_content(text, 'property', 'og:title', seo_title)
    text = set_meta_content(text, 'property', 'og:description', seo_desc)
    text = ensure_large_image_robot(text)
    block = managed_tags(slug, alt)
    if "</head>" not in text.lower():
        raise SystemExit(f"Missing </head>: {path.relative_to(ROOT)}")
    text = re.sub(r'</head>', block + '\n</head>', text, count=1, flags=re.I)
    path.write_text(text, encoding="utf-8")


def canonical_page(rel: str) -> str:
    url = f"{BASE}/{rel}"
    return url[:-10] if url.endswith("index.html") else url


def update_sitemap() -> None:
    p = ROOT / "sitemap.xml"
    text = p.read_text(encoding="utf-8")
    if 'xmlns:image=' not in text:
        text = text.replace(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
        )
    for rel, (slug, alt, _, _, _) in PAGES.items():
        page = canonical_page(rel)
        img = f"{ASSET_BASE}/og/{slug}.jpg"
        block = f'<image:image><image:loc>{escape(img)}</image:loc><image:title>{escape(alt)}</image:title></image:image>'
        pattern = re.compile(r'(<url><loc>' + re.escape(page) + r'</loc>)(.*?)(</url>)', re.S)
        m = pattern.search(text)
        if not m:
            raise SystemExit(f"Page missing from sitemap.xml: {page}")
        body = re.sub(r'<image:image>.*?</image:image>', '', m.group(2), flags=re.S)
        replacement = m.group(1) + body + block + m.group(3)
        text = text[:m.start()] + replacement + text[m.end():]
    p.write_text(text, encoding="utf-8")


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    OG_SRC.mkdir(parents=True, exist_ok=True)
    OG.mkdir(parents=True, exist_ok=True)
    (BRAND / "theory-favicon.svg").write_text(emblem_svg(), encoding="utf-8")
    for rel, (slug, alt, lines, seo_title, seo_desc) in PAGES.items():
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"Missing public page: {rel}")
        if len(seo_title) > 60:
            raise SystemExit(f"SEO title too long ({len(seo_title)}): {rel}")
        if len(seo_desc) > 160:
            raise SystemExit(f"SEO description too long ({len(seo_desc)}): {rel}")
        (OG_SRC / f"{slug}.svg").write_text(cover_svg(lines, alt), encoding="utf-8")
        update_html(path, slug, alt, seo_title, seo_desc)
    update_sitemap()
    print("THEORY SEO source/materialization metadata: PASS")

if __name__ == "__main__":
    main()
