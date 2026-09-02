from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SEP = '<span class="lineage-infinity-separator" aria-hidden="true" title="∞">∞</span>'

HOME_ORDER = [
    "index.html", "theory.html", "hypotheses.html", "novel/",
    "regressor-proposition.html", "unknown.html", "grand-ending.html", "system.html",
    "world.html", "science-constellation.html", "mature-theory-synthesis.html",
    "academic-democracy.html", "open-academic-publishing.html", "bl-adn.html",
    "claims.html", "assets.html", "provenance.html", "critique.html", "author.html",
    "languages.html", "machine.html", "academic-democracy-technology.html",
    "academic-democracy/discovery.html",
]
GROUP_ORDER = [
    "core", "theory", "hypotheses", "narrative", "external-science",
    "mature-theory-synthesis", "claims", "assets", "verification", "machine", "languages"
]
CORE_ORDER = [
    "index.html", "theory.html", "hypotheses.html", "regressor-proposition.html",
    "unknown.html", "grand-ending.html", "system.html", "world.html",
    "academic-democracy.html", "open-academic-publishing.html", "bl-adn.html",
]


def page_language(text: str) -> str:
    match = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, flags=re.I)
    return (match.group(1) if match else "vi").lower()


def page_root(path: Path) -> str:
    rel = path.relative_to(SITE)
    if rel.as_posix() == "404.html":
        return "/bl-infinity/"
    return "../" * (len(rel.parts) - 1)


def make_hypothesis_link(path: Path, mode: str, language: str) -> str:
    root = page_root(path)
    label = "Giả thuyết" if language.startswith("vi") else "Hypotheses"
    current = ' aria-current="page"' if path.relative_to(SITE).as_posix() == "hypotheses.html" else ""
    if mode == "section":
        return f'<a href="{html.escape(root + "hypotheses.html", quote=True)}" data-section="hypotheses"{current}>{html.escape(label)}</a>'
    return f'<a href="{html.escape(root + "hypotheses.html", quote=True)}" data-topic="hypotheses"{current}>{html.escape(label)}</a>'


def replace_three_way_chain(text: str, path: Path, attribute: str) -> str:
    language = page_language(text)
    theory = "theory"
    novel = "novel"
    hypothesis_link = make_hypothesis_link(path, "section" if attribute == "data-section" else "topic", language)
    pattern = re.compile(
        rf'(<a\b(?=[^>]*\b{attribute}="{theory}")[^>]*>.*?</a>)\s*'
        rf'(?:<span class="lineage-infinity-separator"[^>]*>∞</span>\s*)?'
        rf'(?:<a\b(?=[^>]*\b{attribute}="hypotheses")[^>]*>.*?</a>\s*'
        rf'(?:<span class="lineage-infinity-separator"[^>]*>∞</span>\s*)?)?'
        rf'(<a\b(?=[^>]*\b{attribute}="{novel}")[^>]*>.*?</a>)',
        flags=re.I | re.S,
    )
    return pattern.sub(lambda m: m.group(1) + SEP + hypothesis_link + SEP + m.group(2), text, count=1)


def patch_navigation() -> int:
    changed = 0
    for path in SITE.rglob("*.html"):
        if path.name == "404.html":
            continue
        original = path.read_text(encoding="utf-8")
        revised = replace_three_way_chain(original, path, "data-section")
        revised = replace_three_way_chain(revised, path, "data-topic")
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            changed += 1
    return changed


def home_route(item: str) -> str:
    match = re.search(r'<a\s+href="([^"]+)"', item)
    if not match:
        return ""
    route = match.group(1).split("#", 1)[0].split("?", 1)[0].lstrip("./")
    if route == "novel/index.html":
        return "novel/"
    return route


def patch_homepage() -> None:
    path = SITE / "index.html"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r'(<ul class="home-directory-grid">)(.*?)(</ul>)', flags=re.S)
    rank = {route: i for i, route in enumerate(HOME_ORDER)}

    def replace(match: re.Match) -> str:
        items = re.findall(r'<li\b[^>]*>.*?</li>', match.group(2), flags=re.S)
        if not items:
            return match.group(0)
        items.sort(key=lambda item: rank.get(home_route(item), 999))
        return match.group(1) + "".join(items) + match.group(3)

    text = pattern.sub(replace, text, count=1)
    path.write_text(text, encoding="utf-8")


def hypothesis_entries(registry: dict) -> list[dict]:
    entries = [{
        "type": "hypothesis-hub",
        "id": registry.get("branch_id", "BL-HYP"),
        "title": registry.get("title", "BL∞ Hypothesis Branch"),
        "url": "hypotheses.html",
        "status": registry.get("status", "PUBLIC_HYPOTHESIS_BRANCH"),
        "meta": "Theory ≠ Hypothesis ≠ Fiction",
    }]
    for obj in registry.get("objects", []):
        entries.append({
            "type": "hypothesis",
            "id": obj.get("id", ""),
            "title": obj.get("title", obj.get("id", "")),
            "url": "hypotheses.html",
            "status": obj.get("status", ""),
            "meta": obj.get("nonclaim", ""),
        })
    return entries


def patch_scientific_index() -> None:
    index_path = SITE / "machine" / "scientific-index.json"
    registry_path = SITE / "machine" / "hypothesis-registry.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("policy") != "THEORY_NOT_EQUAL_HYPOTHESIS_NOT_EQUAL_FICTION":
        raise RuntimeError("hypothesis epistemic boundary missing")

    groups = [g for g in data.get("groups", []) if g.get("id") != "hypotheses"]
    groups.append({
        "id": "hypotheses",
        "title": "BL∞ hypotheses / Giả thuyết hỗ trợ hệ",
        "entries": hypothesis_entries(registry),
    })
    rank = {gid: i for i, gid in enumerate(GROUP_ORDER)}
    groups.sort(key=lambda g: rank.get(g.get("id", ""), 999))
    data["groups"] = groups

    core = next((g for g in groups if g.get("id") == "core"), None)
    if core is not None:
        entries = core.get("entries", [])
        if not any(e.get("url") == "hypotheses.html" for e in entries):
            entries.append({
                "type": "core",
                "id": "hypotheses.html",
                "title": "Giả thuyết BL∞",
                "url": "hypotheses.html",
                "status": "public",
                "meta": "hypothesis branch",
            })
        core_rank = {route: i for i, route in enumerate(CORE_ORDER)}
        core["title"] = "BL∞ · root, theory, hypotheses and direct branches"
        core["entries"] = sorted(entries, key=lambda e: core_rank.get(e.get("url", ""), 999))

    data["counts"] = {g.get("id", "unknown"): len(g.get("entries", [])) for g in groups}
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def patch_manifest_and_discovery() -> None:
    manifest_path = SITE / "machine" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["hypothesis_hub"] = "../hypotheses.html"
        manifest["hypothesis_registry"] = "hypothesis-registry.json"
        manifest["novel_global_science_weave"] = "novel-global-science-weave.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        url = "https://kimbach91-prog.github.io/bl-infinity/hypotheses.html"
        if f"<loc>{url}</loc>" not in text:
            text = text.replace("</urlset>", f'<url><loc>{url}</loc><lastmod>2026-09-02</lastmod></url>\n</urlset>')
            sitemap.write_text(text, encoding="utf-8")

    llms = SITE / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        marker = "BL∞ hypothesis branch"
        if marker not in text:
            text += (
                "\n\n## BL∞ hypothesis branch\n"
                "Public hub: https://kimbach91-prog.github.io/bl-infinity/hypotheses.html\n"
                "Boundary: Theory != Hypothesis != Fiction. Hypotheses may support research generation but do not inherit truth authority.\n"
                "Narrative science continuity: machine/novel-global-science-weave.json\n"
            )
            llms.write_text(text, encoding="utf-8")


def patch_css() -> None:
    path = SITE / "assets" / "css" / "navigation-system.css"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "/* BL-HYP three-way infinity chain */"
    if marker in text:
        return
    text += '''\n/* BL-HYP three-way infinity chain */
.topic-bar a[data-topic="theory"],.topic-bar a[data-topic="hypotheses"],.topic-bar a[data-topic="novel"]{border-color:rgba(125,21,21,.14);background:#fff}
.topic-bar a[data-topic="hypotheses"]{border-radius:7px}
.top nav a[data-section="hypotheses"]{font-weight:820}
.home-directory-grid li:first-child a{border-color:rgba(125,21,21,.42);background:linear-gradient(135deg,var(--accent-soft),#fff)}
.home-directory-grid li:first-child strong{color:var(--accent)}
'''
    path.write_text(text, encoding="utf-8")


def verify() -> None:
    nav_checked = topic_checked = 0
    chain = re.compile(
        r'<a\b(?=[^>]*\bdata-section="theory")[^>]*>.*?</a>'
        r'<span class="lineage-infinity-separator"[^>]*>∞</span>'
        r'<a\b(?=[^>]*\bdata-section="hypotheses")[^>]*>.*?</a>'
        r'<span class="lineage-infinity-separator"[^>]*>∞</span>'
        r'<a\b(?=[^>]*\bdata-section="novel")[^>]*>.*?</a>', re.I | re.S)
    topic_chain = re.compile(
        r'<a\b(?=[^>]*\bdata-topic="theory")[^>]*>.*?</a>'
        r'<span class="lineage-infinity-separator"[^>]*>∞</span>'
        r'<a\b(?=[^>]*\bdata-topic="hypotheses")[^>]*>.*?</a>'
        r'<span class="lineage-infinity-separator"[^>]*>∞</span>'
        r'<a\b(?=[^>]*\bdata-topic="novel")[^>]*>.*?</a>', re.I | re.S)
    for path in SITE.rglob("*.html"):
        if path.name == "404.html":
            continue
        text = path.read_text(encoding="utf-8")
        if 'data-section="theory"' in text and 'data-section="novel"' in text:
            if not chain.search(text):
                raise RuntimeError(f"three-way primary chain missing: {path.relative_to(SITE)}")
            nav_checked += 1
        if 'data-topic="theory"' in text and 'data-topic="novel"' in text:
            if not topic_chain.search(text):
                raise RuntimeError(f"three-way topic chain missing: {path.relative_to(SITE)}")
            topic_checked += 1

    home = (SITE / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<ul class="home-directory-grid">(.*?)</ul>', home, re.S)
    if not match:
        raise RuntimeError("homepage directory missing")
    items = re.findall(r'<li\b[^>]*>.*?</li>', match.group(1), re.S)
    first = [home_route(item) for item in items[:4]]
    if first != ["index.html", "theory.html", "hypotheses.html", "novel/"]:
        raise RuntimeError(f"BL∞ root hierarchy mismatch: {first}")

    index = json.loads((SITE / "machine" / "scientific-index.json").read_text(encoding="utf-8"))
    groups = [g.get("id") for g in index.get("groups", [])]
    if groups[:4] != ["core", "theory", "hypotheses", "narrative"]:
        raise RuntimeError(f"Scientific Index root hierarchy mismatch: {groups[:4]}")
    core = index["groups"][0].get("entries", [])
    core_urls = [e.get("url") for e in core[:3]]
    if core_urls != ["index.html", "theory.html", "hypotheses.html"]:
        raise RuntimeError(f"Scientific Index core order mismatch: {core_urls}")

    if not (SITE / "hypotheses.html").exists():
        raise RuntimeError("hypotheses page missing")
    if not (SITE / "machine" / "hypothesis-registry.json").exists():
        raise RuntimeError("hypothesis registry missing")
    chapter = (SITE / "novel" / "chapter-001.html").read_text(encoding="utf-8")
    if 'id="global-science-continuity-weave"' not in chapter:
        raise RuntimeError("global science continuity weave missing from chapter 1")
    print(f"BL∞ root + Theory ∞ Hypotheses ∞ Novel verified: nav={nav_checked}, topic={topic_checked}")


def main() -> None:
    changed = patch_navigation()
    patch_homepage()
    patch_scientific_index()
    patch_manifest_and_discovery()
    patch_css()
    verify()
    print(f"Final hypothesis/science hierarchy patch applied: {changed} HTML navigation surfaces changed")


if __name__ == "__main__":
    main()
