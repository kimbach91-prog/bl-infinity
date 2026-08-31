from pathlib import Path
import base64
import hashlib
import html
import json
import re
import shutil

import mistune
import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CFG = yaml.safe_load((ROOT / "bl.config.yml").read_text(encoding="utf-8"))
TINDEX = json.loads((ROOT / "translations/translation-index.json").read_text(encoding="utf-8"))
SAFE_MD = mistune.create_markdown(escape=True, plugins=["table", "strikethrough", "task_lists"])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csp_hash(text: str) -> str:
    digest = base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")
    return f"'sha256-{digest}'"


def csp_for(html_text: str) -> str:
    script_hashes = [
        csp_hash(body)
        for body in re.findall(
            r"<script\s+type=['\"]application/ld\+json['\"]\s*>(.*?)</script>",
            html_text,
            flags=re.I | re.S,
        )
    ]
    style_hashes = [
        csp_hash(body)
        for body in re.findall(r"<style\b[^>]*>(.*?)</style>", html_text, flags=re.I | re.S)
    ]
    script_src = " ".join(["'self'", "https://giscus.app"] + script_hashes)
    style_src = " ".join(["'self'"] + style_hashes)
    return (
        "default-src 'self'; "
        f"script-src {script_src}; "
        f"style-src {style_src}; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "frame-src https://giscus.app; "
        "connect-src 'self' https://giscus.app; "
        "object-src 'none'; base-uri 'self'; "
        "form-action 'self' https://github.com; upgrade-insecure-requests"
    )


def inject_security(html_text: str) -> str:
    if 'http-equiv="Content-Security-Policy"' not in html_text:
        meta = (
            f'<meta http-equiv="Content-Security-Policy" content="{html.escape(csp_for(html_text), quote=True)}">'
            '<meta name="referrer" content="strict-origin-when-cross-origin">'
        )
        html_text = html_text.replace("</head>", meta + "</head>", 1)
    return html_text


def paired_links(vi_url: str, en_url: str, xdefault: str) -> str:
    return (
        f'<link rel="alternate" hreflang="vi" href="{html.escape(vi_url, quote=True)}">'
        f'<link rel="alternate" hreflang="en" href="{html.escape(en_url, quote=True)}">'
        f'<link rel="alternate" hreflang="x-default" href="{html.escape(xdefault, quote=True)}">'
    )


def inject_pairing(path: Path, vi_url: str, en_url: str, en_href: str) -> None:
    text = path.read_text(encoding="utf-8")
    if 'hreflang="en"' not in text:
        text = text.replace("</head>", paired_links(vi_url, en_url, vi_url) + "</head>", 1)
    if 'class="lang-switch"' not in text:
        text = text.replace(
            "</nav>",
            f'<a class="lang-switch" href="{html.escape(en_href, quote=True)}" hreflang="en" lang="en">EN</a></nav>',
            1,
        )
    path.write_text(inject_security(text), encoding="utf-8")


def inject_academic_democracy_technology_link(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    href = "academic-democracy-technology.html"
    if href not in text:
        text = text.replace(
            "</nav>",
            f'<a href="{href}">Technology Profile</a></nav>',
            1,
        )
    path.write_text(inject_security(text), encoding="utf-8")


def giscus_en() -> str:
    c = CFG.get("comments", {})
    required = ["repo", "repo_id", "category", "category_id"]
    if not c.get("enabled") or not all(c.get(k) for k in required):
        return ""
    return (
        '<section class="comments"><h2>Public critique</h2>'
        '<script src="https://giscus.app/client.js" '
        f'data-repo="{html.escape(c["repo"], quote=True)}" '
        f'data-repo-id="{html.escape(c["repo_id"], quote=True)}" '
        f'data-category="{html.escape(c["category"], quote=True)}" '
        f'data-category-id="{html.escape(c["category_id"], quote=True)}" '
        'data-mapping="pathname" data-strict="1" data-reactions-enabled="1" '
        'data-emit-metadata="0" data-input-position="top" data-theme="light" '
        'data-lang="en" crossorigin="anonymous" async></script></section>'
    )


def english_page(title: str, description: str, canonical: str, vi_url: str, body: str) -> str:
    base = "../"
    page = f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
{paired_links(vi_url, canonical, vi_url)}
<meta property="og:type" content="article"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(description, quote=True)}"><meta property="og:url" content="{html.escape(canonical, quote=True)}">
<meta property="og:locale" content="en_US"><meta property="og:locale:alternate" content="vi_VN">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{html.escape(title, quote=True)}"><meta name="twitter:description" content="{html.escape(description, quote=True)}">
<link rel="stylesheet" href="{base}assets/css/main.css"><link rel="alternate" type="application/rss+xml" title="BL∞ updates" href="{base}feed.xml">
</head><body><header class="top"><a href="index.html" class="brand">BL∞</a><span>Bach Lam – Optimizer</span>
<nav><a href="theory.html">Theory</a><a href="{base}academic-democracy-technology.html">Technology Profile</a><a href="{base}bl-adn.html">BL-ADN</a><a href="{base}claims.html">Claims</a><a href="{base}assets.html">Assets</a><a href="{base}provenance.html">Provenance</a><a href="{base}critique.html">Critique</a><a href="{base}machine.html">Machine</a><a class="lang-switch" href="{html.escape(vi_url, quote=True)}" hreflang="vi" lang="vi">VI</a></nav></header>
<main><article>{body}</article>{giscus_en()}</main>
<footer><p>BL∞ · {html.escape(str(CFG['project']['version']))} · English derivative research edition. <a href="{base}machine/translation-status.json">Translation status</a> · <a href="{base}machine/manifest.json">Machine manifest</a></p></footer>
<script src="{base}assets/js/site.js"></script></body></html>'''
    return inject_security(page)


def build_english() -> None:
    en_dir = SITE / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    root_url = CFG["project"]["canonical_url"].rstrip("/") + "/"
    readme = SAFE_MD((ROOT / "translations/en/README.md").read_text(encoding="utf-8"))
    theory = SAFE_MD((ROOT / "translations/en/THEORY_CORE.md").read_text(encoding="utf-8"))
    desc = (
        "English research edition of BL∞: finite observers, open ontology, reachability, "
        "public critique, provenance, security and protected runtime boundaries."
    )
    (en_dir / "index.html").write_text(
        english_page("BL∞ — Bach Lam Infinity Proposition", desc, root_url + "en/", root_url, readme),
        encoding="utf-8",
    )
    (en_dir / "theory.html").write_text(
        english_page(
            "BL∞ — English Core Research Edition",
            desc,
            root_url + "en/theory.html",
            root_url + "theory.html",
            theory,
        ),
        encoding="utf-8",
    )


def write_translation_status() -> None:
    en = TINDEX["languages"]["en"]
    sources = {rel: "sha256:" + sha256_file(ROOT / rel) for rel in en["source_files"]}
    translations = {rel: "sha256:" + sha256_file(ROOT / rel) for rel in en["translation_files"]}
    status = {
        "schema_version": "1.0",
        "source_language": TINDEX["source_language"],
        "policy": TINDEX["policy"],
        "languages": TINDEX["languages"],
        "source_hashes": sources,
        "translation_hashes": translations,
        "translation_index_hash": "sha256:" + sha256_file(ROOT / "translations/translation-index.json"),
    }
    (SITE / "machine/translation-status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copy(ROOT / "machine/security-profile.json", SITE / "machine/security-profile.json")
    (SITE / "translations").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "translations/translation-index.json", SITE / "translations/translation-index.json")


def enrich_manifest() -> None:
    path = SITE / "machine/manifest.json"
    if not path.exists():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["languages"] = {
        "vi": {"role": "FULL_CANONICAL_PUBLIC_READING_SOURCE", "entry": "../theory.html"},
        "en": {"role": "CORE_RESEARCH_EDITION", "entry": "../en/theory.html"},
    }
    manifest["translation_status"] = "translation-status.json"
    manifest["translation_index"] = "../translations/translation-index.json"
    manifest["security_profile"] = "security-profile.json"
    manifest["security_policy"] = "https://github.com/kimbach91-prog/bl-infinity/blob/main/SECURITY.md"
    manifest["academic_democracy_technology_profile"] = "../academic-democracy-technology.html"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def update_discovery() -> None:
    root_url = CFG["project"]["canonical_url"].rstrip("/") + "/"
    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        additions = []
        for url in [
            root_url + "en/",
            root_url + "en/theory.html",
            root_url + "academic-democracy-technology.html",
        ]:
            if url not in text:
                additions.append(
                    f'<url><loc>{html.escape(url)}</loc><lastmod>{CFG["project"].get("last_updated", CFG["project"]["date"])}</lastmod></url>'
                )
        if additions:
            text = text.replace("</urlset>", "\n".join(additions) + "\n</urlset>")
            sitemap.write_text(text, encoding="utf-8")
    llms = SITE / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        block = (
            "\n\nBilingual public entry points:\n"
            "- Vietnamese full theory: " + root_url + "theory.html\n"
            "- English core research edition: " + root_url + "en/theory.html\n"
            "- Academic Democracy technology profile: " + root_url + "academic-democracy-technology.html\n"
            "- Translation status: " + root_url + "machine/translation-status.json\n"
            "- Public security profile: " + root_url + "machine/security-profile.json\n"
        )
        if "English core research edition" not in text:
            llms.write_text(text + block, encoding="utf-8")
        elif "Academic Democracy technology profile" not in text:
            llms.write_text(text + "\n- Academic Democracy technology profile: " + root_url + "academic-democracy-technology.html\n", encoding="utf-8")


def harden_all_html() -> None:
    for path in SITE.rglob("*.html"):
        path.write_text(inject_security(path.read_text(encoding="utf-8")), encoding="utf-8")


if not SITE.exists():
    raise SystemExit("site/ missing: run scripts/build.py first")

root_url = CFG["project"]["canonical_url"].rstrip("/") + "/"
build_english()
if (SITE / "index.html").exists():
    inject_pairing(SITE / "index.html", root_url, root_url + "en/", "en/")
if (SITE / "theory.html").exists():
    inject_pairing(
        SITE / "theory.html",
        root_url + "theory.html",
        root_url + "en/theory.html",
        "en/theory.html",
    )
inject_academic_democracy_technology_link(SITE / "academic-democracy.html")
write_translation_status()
enrich_manifest()
update_discovery()
harden_all_html()
print("Hardened public site, generated bilingual English entry points, and linked Academic Democracy technology profile")
