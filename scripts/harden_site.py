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


def inject_language_switch(path: Path, href: str, hreflang: str, label: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if 'class="lang-switch"' not in text:
        text = text.replace(
            "</nav>",
            f'<a class="lang-switch" href="{html.escape(href, quote=True)}" '
            f'hreflang="{html.escape(hreflang, quote=True)}" '
            f'lang="{html.escape(hreflang, quote=True)}">{html.escape(label)}</a></nav>',
            1,
        )
    path.write_text(text, encoding="utf-8")


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


def english_page(title: str, description: str, canonical: str, vi_url: str, body: str, base: str = "../", head_extra: str = "", og_type: str = "article") -> str:
    page = f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
{paired_links(vi_url, canonical, vi_url)}
<meta property="og:type" content="{html.escape(og_type, quote=True)}"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(description, quote=True)}"><meta property="og:url" content="{html.escape(canonical, quote=True)}">
<meta property="og:locale" content="en_US"><meta property="og:locale:alternate" content="vi_VN">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{html.escape(title, quote=True)}"><meta name="twitter:description" content="{html.escape(description, quote=True)}">
<link rel="stylesheet" href="{base}assets/css/main.css"><link rel="alternate" type="application/rss+xml" title="BL∞ updates" href="{base}feed.xml">
{head_extra}
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
    readme += '''<section class="topic-entry-points" aria-labelledby="topic-entry-en"><p class="eyebrow">Topic entry points</p><h2 id="topic-entry-en">Four public research clusters</h2><div class="topic-grid"><section><h3><a href="../academic-democracy/en/">Academic Democracy</a></h3><p>Open entry to knowledge creation with evidence weighting, public critique and reality veto.</p></section><section><h3><a href="../bl-adn.html">Research provenance</a></h3><p>Traceable authorship, source lineage, AI-formalization roles and version history.</p></section><section><h3><a href="../machine.html">Machine-readable scholarship</a></h3><p>Claim IDs, registries, dependency graphs and public machine contracts.</p></section><section><h3><a href="../critique.html">Public critique</a></h3><p>Counterexamples, evidence and inference defects attached to the exact research object.</p></section></div></section>'''
    theory = SAFE_MD((ROOT / "translations/en/THEORY_CORE.md").read_text(encoding="utf-8"))
    home_desc = "English overview of BL∞ by Lâm Kim Bách: the Bach Lam Infinity Proposition, Academic Democracy, research provenance, machine-readable scholarship and public critique."
    theory_desc = "English core research edition of BL∞: finite observers, open ontology, possibility, reachability, provenance, public critique and protected runtime boundaries."
    def schema(name: str, url: str, vi_url: str, description: str) -> str:
        obj = {
            "@context": "https://schema.org", "@type": "CreativeWork", "name": name,
            "url": url, "mainEntityOfPage": url, "inLanguage": "en", "isBasedOn": vi_url,
            "description": description, "version": CFG["project"]["version"],
            "dateModified": CFG["project"].get("last_updated", CFG["project"]["date"]),
            "author": {"@type": "Person", "@id": root_url + "author.html#person", "name": "Lâm Kim Bách", "url": root_url + "author.html"},
        }
        return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"
    (en_dir / "index.html").write_text(
        english_page("BL∞ — Bach Lam Infinity Proposition", home_desc, root_url + "en/", root_url, readme, head_extra=schema("BL∞ — Bach Lam Infinity Proposition", root_url + "en/", root_url, home_desc)),
        encoding="utf-8",
    )
    (en_dir / "theory.html").write_text(
        english_page(
            "BL∞ — English Core Research Edition",
            theory_desc,
            root_url + "en/theory.html",
            root_url + "theory.html",
            theory,
            head_extra=schema("BL∞ — English Core Research Edition", root_url + "en/theory.html", root_url + "theory.html", theory_desc),
        ),
        encoding="utf-8",
    )


def build_author_english() -> None:
    root_url = CFG["project"]["canonical_url"].rstrip("/") + "/"
    author_url = root_url + "author/en/"
    vi_url = root_url + "author.html"
    person_id = vi_url + "#person"
    person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "@id": person_id,
        "name": "Lâm Kim Bách",
        "alternateName": ["Bách Lâm", "Bách Lâm – Optimizer", "Lam Kim Bach", "Bach Lam"],
        "url": vi_url,
        "sameAs": ["https://m.facebook.com/lam.kimbach/", "https://github.com/kimbach91-prog"],
        "knowsAbout": ["BL∞", "Academic Democracy", "research provenance", "epistemic governance", "AI-assisted scholarship"],
    }
    profile = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "@id": author_url + "#profile",
        "url": author_url,
        "dateModified": CFG["project"].get("last_updated", CFG["project"]["date"]),
        "mainEntity": {"@id": person_id},
        "inLanguage": "en",
    }
    head_extra = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": [person, profile]}, ensure_ascii=False) + "</script>"
    body = '''<section class="author-hero"><div class="author-monogram" aria-hidden="true">LKB∞</div><div>
<p class="eyebrow">Canonical author profile</p><h1>Lâm Kim Bách</h1>
<p class="author-lead">Originating author of BL∞; authorial/lineage identity <strong>Bách Lâm</strong>; public system/method identity <strong>Optimizer</strong>.</p>
<p><a class="primary-link" href="../../en/theory.html">Read the BL∞ core edition</a> · <a href="../../author.html" hreflang="vi" lang="vi">Hồ sơ tiếng Việt</a></p></div></section>
<div class="identity-grid"><section><h2>Human identity</h2><p>Lâm Kim Bách</p></section><section><h2>Authorial lineage</h2><p>Bách Lâm</p></section><section><h2>Public system/method</h2><p>Optimizer</p></section></div>
<p>Lâm Kim Bách originated BL∞ — the Bach Lam Infinity Proposition — and the Academic Democracy line of inquiry published within the BL lineage. AI supports formalization, editing, translation and structural checks; it does not replace the intellectual origin of an object.</p>
<p><strong>Provenance boundary:</strong> AI formalization is not a verbatim quotation from Bách Lâm. Relation, similarity or use of a general term does not by itself establish authorship.</p>
<h2>Verified public profiles</h2><ul><li><a rel="me" href="https://m.facebook.com/lam.kimbach/">Facebook — Lâm Kim Bách</a></li><li><a rel="me" href="https://github.com/kimbach91-prog">GitHub — @kimbach91-prog</a></li></ul>
<h2>Canonical public works</h2><ul><li><a href="../../en/theory.html">BL∞ — English core research edition</a></li><li><a href="../../academic-democracy/en/">Academic Democracy — discovery summary</a></li><li><a href="../../bl-adn.html">BL-ADN — intellectual-lineage protocol (Vietnamese source)</a></li><li><a href="../../critique.html">Public critique protocol</a></li></ul>'''
    page = english_page(
        "Lâm Kim Bách (Bách Lâm) — Author of BL∞",
        "Canonical English author profile for Lâm Kim Bách: Bách Lâm authorial lineage, Optimizer public method, BL∞, Academic Democracy and public provenance.",
        author_url,
        vi_url,
        body,
        base="../../",
        head_extra=head_extra,
        og_type="profile",
    )
    dest = SITE / "author" / "en" / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


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
        "discovery_generator_hash": "sha256:" + sha256_file(ROOT / "scripts/build_discovery.py"),
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
    manifest["discovery_languages"] = TINDEX.get("discovery_editions", {})
    manifest["translation_status"] = "translation-status.json"
    manifest["translation_index"] = "../translations/translation-index.json"
    manifest["language_hub"] = "../languages.html"
    manifest["author_profile"] = "../author.html"
    manifest["author_profile_en"] = "../author/en/"
    manifest["academic_democracy_discovery"] = "academic-democracy-discovery.json"
    manifest["unified_system"] = "bl-infinity-unified-system.json"
    manifest["constituent_registry"] = "unified-constituents.json"
    manifest["reality_gia_tai_topology"] = "reality-gia-tai-topology.json"
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
            root_url + "author/en/",
            root_url + "languages.html",
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
            "- Canonical author profile: " + root_url + "author.html\n"
            "- English author profile: " + root_url + "author/en/\n"
            "- Language scope hub: " + root_url + "languages.html\n"
            "- Unified system contract: " + root_url + "machine/bl-infinity-unified-system.json\n"
            "- Unified constituents: " + root_url + "machine/unified-constituents.json\n"
            "- Reality–GiaTai topology: " + root_url + "machine/reality-gia-tai-topology.json\n"
            "- Translation status: " + root_url + "machine/translation-status.json\n"
            "- Public security profile: " + root_url + "machine/security-profile.json\n"
        )
        if "English core research edition" not in text:
            llms.write_text(text + block, encoding="utf-8")
        elif "Academic Democracy technology profile" not in text:
            llms.write_text(text + "\n- Academic Democracy technology profile: " + root_url + "academic-democracy-technology.html\n", encoding="utf-8")


def project_root_path() -> str:
    suffix = CFG["project"]["canonical_url"].split("/", 3)[-1].strip("/")
    return f"/{suffix}/" if suffix else "/"


def page_root(path: Path) -> str:
    rel = path.relative_to(SITE)
    if rel.as_posix() == "404.html":
        return project_root_path()
    return "../" * (len(rel.parts) - 1)


def page_language(text: str) -> str:
    match = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, flags=re.I)
    return match.group(1).lower() if match else "vi"


def language_menu(path: Path, language: str) -> str:
    root = page_root(path)
    rel = path.relative_to(SITE).as_posix()
    vietnamese = language.startswith("vi")
    title = "Ngôn ngữ +" if vietnamese else "Languages +"
    aria = "Chọn ngôn ngữ và xem phạm vi bản dịch" if vietnamese else "Choose a language and inspect translation scope"
    primary_label = "Bản đọc chính" if vietnamese else "Primary reading editions"
    draft_label = "Bản khám phá Dân chủ Học thuật" if vietnamese else "Academic Democracy discovery drafts"
    scope_label = "Phạm vi & chất lượng bản dịch" if vietnamese else "Translation scope & quality"

    vi_route, en_route = "index.html", "en/"
    if rel in {"theory.html", "en/theory.html"}:
        vi_route, en_route = "theory.html", "en/theory.html"
    elif rel in {"author.html", "author/en/index.html"}:
        vi_route, en_route = "author.html", "author/en/"
    elif rel == "academic-democracy.html" or rel.startswith("academic-democracy/"):
        vi_route, en_route = "academic-democracy.html", "academic-democracy/en/"
    core = [
        ("vi", "Tiếng Việt", root + vi_route, "canonical", vi_route),
        ("en", "English", root + en_route, "core", en_route + "index.html" if en_route.endswith("/") else en_route),
    ]
    core_links = []
    for code, name, href, status, current_route in core:
        current = ' aria-current="page"' if rel == current_route else ""
        core_links.append(
            f'<a href="{html.escape(href, quote=True)}" hreflang="{code}" lang="{code}"{current}>'
            f'<span>{html.escape(name)}</span><small>{status}</small></a>'
        )

    draft_links = []
    for item in TINDEX.get("discovery_editions", {}).get("languages", {}).values():
        if item["hreflang"] == "en":
            continue
        route = item["route"]
        current = ' aria-current="page"' if rel == route + "index.html" else ""
        draft_links.append(
            f'<a href="{html.escape(root + route, quote=True)}" hreflang="{html.escape(item["hreflang"], quote=True)}" '
            f'lang="{html.escape(item["hreflang"], quote=True)}"{current}>'
            f'<span>{html.escape(item["name"])}</span><small>discovery draft</small></a>'
        )

    return (
        f'<details class="language-menu"><summary aria-label="{html.escape(aria, quote=True)}">{html.escape(title)}</summary>'
        '<div class="language-menu-panel">'
        f'<p class="language-menu-title">{html.escape(primary_label)}</p>'
        + "".join(core_links)
        + f'<p class="language-menu-title">{html.escape(draft_label)}</p>'
        + "".join(draft_links)
        + f'<a class="language-scope-link" href="{html.escape(root + "languages.html", quote=True)}">{html.escape(scope_label)} →</a>'
        + "</div></details>"
    )


def navigation_link(href: str, label: str, section: str, current: str | None = None, extra_class: str = "") -> str:
    attrs = [f'href="{html.escape(href, quote=True)}"', f'data-section="{section}"']
    if current:
        attrs.append(f'aria-current="{current}"')
    if extra_class:
        attrs.append(f'class="{extra_class}"')
    return f'<a {" ".join(attrs)}>{html.escape(label)}</a>'


def normalize_navigation(path: Path, text: str) -> str:
    if 'class="top"' not in text:
        return text
    rel = path.relative_to(SITE).as_posix()
    root = page_root(path)
    language = page_language(text)
    vietnamese = language.startswith("vi")
    english_core = language.startswith("en")
    localized_match = re.fullmatch(r"academic-democracy/([^/]+)/index\.html", rel)

    labels = {
        "theory": "Học thuyết" if vietnamese else "Theory",
        "academic": "Dân chủ Học thuật" if vietnamese else "Academic Democracy",
        "adn": "BL-ADN",
        "claims": "Claims",
        "assets": "Assets",
        "author": "Tác giả" if vietnamese else "Author",
        "provenance": "Provenance",
        "critique": "Phản biện" if vietnamese else "Critique",
        "machine": "Machine",
    }
    theory_href = root + ("en/theory.html" if english_core else "theory.html")
    if localized_match:
        academic_href = root + f"academic-democracy/{localized_match.group(1)}/"
    else:
        academic_href = root + ("academic-democracy/en/" if english_core else "academic-democracy.html")
    author_href = root + ("author/en/" if english_core else "author.html")
    brand_href = root + ("en/" if english_core else "index.html")

    current_section = None
    current_kind = None
    if rel in {"theory.html", "en/theory.html"}:
        current_section, current_kind = "theory", "page"
    elif rel == "academic-democracy.html" or localized_match:
        current_section, current_kind = "academic", "page"
    elif rel == "academic-democracy/discovery.html" or rel == "academic-democracy-technology.html":
        current_section, current_kind = "academic", "location"
    elif rel == "bl-adn.html":
        current_section, current_kind = "adn", "page"
    elif rel == "claims.html":
        current_section, current_kind = "claims", "page"
    elif rel.startswith("claims/"):
        current_section, current_kind = "claims", "location"
    elif rel == "assets.html":
        current_section, current_kind = "assets", "page"
    elif rel.startswith("assets/"):
        current_section, current_kind = "assets", "location"
    elif rel in {"author.html", "author/en/index.html"}:
        current_section, current_kind = "author", "page"
    elif rel == "provenance.html":
        current_section, current_kind = "provenance", "page"
    elif rel == "critique.html":
        current_section, current_kind = "critique", "page"
    elif rel == "machine.html":
        current_section, current_kind = "machine", "page"

    targets = [
        ("theory", theory_href),
        ("academic", academic_href),
        ("adn", root + "bl-adn.html"),
        ("claims", root + "claims.html"),
        ("assets", root + "assets.html"),
        ("author", author_href),
        ("provenance", root + "provenance.html"),
        ("critique", root + "critique.html"),
        ("machine", root + "machine.html"),
    ]
    links = [
        navigation_link(href, labels[key], key, current_kind if current_section == key else None)
        for key, href in targets
    ]
    if "academic-democracy" in rel:
        links.append(navigation_link(root + "academic-democracy/discovery.html", "Discovery", "academic-discovery", "page" if rel == "academic-democracy/discovery.html" else None, "context-link"))
        links.append(navigation_link(root + "academic-democracy-technology.html", "Technology", "academic-technology", "page" if rel == "academic-democracy-technology.html" else None, "context-link"))

    pair = None
    if rel == "index.html":
        pair = (root + "en/", "en", "EN")
    elif rel == "en/index.html":
        pair = (root + "index.html", "vi", "VI")
    elif rel == "theory.html":
        pair = (root + "en/theory.html", "en", "EN")
    elif rel == "en/theory.html":
        pair = (root + "theory.html", "vi", "VI")
    elif rel == "academic-democracy.html":
        pair = (root + "academic-democracy/en/", "en", "EN")
    elif rel == "academic-democracy/en/index.html":
        pair = (root + "academic-democracy.html", "vi", "VI")
    elif rel == "author.html":
        pair = (root + "author/en/", "en", "EN")
    elif rel == "author/en/index.html":
        pair = (root + "author.html", "vi", "VI")
    if pair:
        links.append(
            f'<a class="lang-switch" href="{html.escape(pair[0], quote=True)}" '
            f'hreflang="{pair[1]}" lang="{pair[1]}">{pair[2]}</a>'
        )

    nav = '<nav aria-label="Primary">' + "".join(links) + "</nav>"
    text = re.sub(r"<nav\b[^>]*>.*?</nav>", nav, text, count=1, flags=re.I | re.S)
    active_brand = ' aria-current="page"' if rel in {"index.html", "en/index.html"} else ""
    text = re.sub(
        r'<a\s+href="[^"]*"\s+class="brand"(?:\s+aria-current="page")?',
        f'<a href="{html.escape(brand_href, quote=True)}" class="brand"{active_brand}',
        text,
        count=1,
        flags=re.I,
    )
    text = re.sub(
        r"<span>([^<]*Optimizer[^<]*)</span>",
        lambda match: f'<a class="author-mark" href="{html.escape(author_href, quote=True)}">{match.group(1)}</a>',
        text,
        count=1,
        flags=re.I,
    )
    if 'class="language-menu"' not in text:
        text = text.replace("</nav>", "</nav>" + language_menu(path, language), 1)
    return text


def inject_accessibility(path: Path, text: str) -> str:
    language = page_language(text)
    label = "Bỏ qua điều hướng, tới nội dung chính" if language.startswith("vi") else "Skip navigation and go to main content"
    if 'id="main-content"' not in text:
        text = text.replace("<main>", '<main id="main-content" tabindex="-1">', 1)
    if 'class="skip-link"' not in text:
        text = text.replace("<body>", f'<body><a class="skip-link" href="#main-content">{html.escape(label)}</a>', 1)
    return text


def harden_all_html() -> None:
    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        text = normalize_navigation(path, text)
        text = inject_accessibility(path, text)
        if 'class="top"' in text and "assets/js/site.js" not in text:
            depth = len(path.relative_to(SITE).parts) - 1
            src = "../" * depth + "assets/js/site.js"
            text = text.replace(
                "</body>",
                f'<script src="{html.escape(src, quote=True)}"></script></body>',
                1,
            )
        path.write_text(inject_security(text), encoding="utf-8")


if not SITE.exists():
    raise SystemExit("site/ missing: run scripts/build.py first")

root_url = CFG["project"]["canonical_url"].rstrip("/") + "/"
build_english()
build_author_english()
if (SITE / "index.html").exists():
    inject_pairing(SITE / "index.html", root_url, root_url + "en/", "en/")
if (SITE / "theory.html").exists():
    inject_pairing(
        SITE / "theory.html",
        root_url + "theory.html",
        root_url + "en/theory.html",
        "en/theory.html",
    )
if (SITE / "academic-democracy.html").exists():
    inject_language_switch(
        SITE / "academic-democracy.html",
        "academic-democracy/en/",
        "en",
        "EN summary",
    )
if (SITE / "author.html").exists():
    inject_pairing(
        SITE / "author.html",
        root_url + "author.html",
        root_url + "author/en/",
        "author/en/",
    )
inject_language_switch(
    SITE / "academic-democracy/en/index.html",
    "../../academic-democracy.html",
    "vi",
    "VI",
)
inject_academic_democracy_technology_link(SITE / "academic-democracy.html")
write_translation_status()
enrich_manifest()
update_discovery()
harden_all_html()
print("Hardened public site, generated bilingual English entry points, and linked Academic Democracy technology profile")
