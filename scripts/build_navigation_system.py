from pathlib import Path
import html
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CFG = __import__("yaml").safe_load((ROOT / "bl.config.yml").read_text(encoding="utf-8"))
CLAIMS = json.loads((ROOT / "claims/claims.json").read_text(encoding="utf-8"))
ASSETS = json.loads((ROOT / "machine/assets.json").read_text(encoding="utf-8"))
TINDEX = json.loads((ROOT / "translations/translation-index.json").read_text(encoding="utf-8"))

LANG_UI = {
    "vi": {"overview":"Tổng quan","theory":"Học thuyết","regressor":"Kẻ Hồi Quy","system":"Hệ thống","academic":"Dân chủ Học thuật","novel":"Tiểu thuyết","claims":"Claims","critique":"Phản biện","aria":"Điều hướng chủ đề"},
    "en": {"overview":"Overview","theory":"Theory","regressor":"Regressor","system":"System","academic":"Academic Democracy","novel":"Novel","claims":"Claims","critique":"Critique","aria":"Topic navigation"},
    "es": {"overview":"Inicio","theory":"Teoría","regressor":"Regresor","system":"Sistema","academic":"Democracia académica","novel":"Novela","claims":"Claims","critique":"Crítica","aria":"Navegación temática"},
    "fr": {"overview":"Accueil","theory":"Théorie","regressor":"Régresseur","system":"Système","academic":"Démocratie académique","novel":"Roman","claims":"Claims","critique":"Critique","aria":"Navigation thématique"},
    "de": {"overview":"Übersicht","theory":"Theorie","regressor":"Regressor","system":"System","academic":"Akademische Demokratie","novel":"Roman","claims":"Claims","critique":"Kritik","aria":"Thematische Navigation"},
    "pt": {"overview":"Visão geral","theory":"Teoria","regressor":"Regressor","system":"Sistema","academic":"Democracia acadêmica","novel":"Romance","claims":"Claims","critique":"Crítica","aria":"Navegação temática"},
    "zh": {"overview":"总览","theory":"理论","regressor":"回归者","system":"系统","academic":"学术民主","novel":"小说","claims":"主张","critique":"批评","aria":"主题导航"},
    "ja": {"overview":"概要","theory":"理論","regressor":"回帰者","system":"システム","academic":"学術民主主義","novel":"小説","claims":"主張","critique":"批評","aria":"トピックナビゲーション"},
    "ko": {"overview":"개요","theory":"이론","regressor":"회귀자","system":"시스템","academic":"학술 민주주의","novel":"소설","claims":"주장","critique":"비평","aria":"주제 탐색"},
    "ru": {"overview":"Обзор","theory":"Теория","regressor":"Регрессор","system":"Система","academic":"Академическая демократия","novel":"Роман","claims":"Claims","critique":"Критика","aria":"Навигация по темам"},
    "ar": {"overview":"نظرة عامة","theory":"النظرية","regressor":"الراجع","system":"النظام","academic":"الديمقراطية الأكاديمية","novel":"الرواية","claims":"الادعاءات","critique":"النقد","aria":"التنقل الموضوعي"},
    "hi": {"overview":"अवलोकन","theory":"सिद्धांत","regressor":"रिग्रेसर","system":"प्रणाली","academic":"शैक्षणिक लोकतंत्र","novel":"उपन्यास","claims":"दावे","critique":"आलोचना","aria":"विषय नेविगेशन"},
    "id": {"overview":"Ringkasan","theory":"Teori","regressor":"Regresor","system":"Sistem","academic":"Demokrasi Akademik","novel":"Novel","claims":"Klaim","critique":"Kritik","aria":"Navigasi topik"},
}


def slug(value: str) -> str:
    value = value.replace("∞", "infinity").replace("–", "-").replace("—", "-")
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()
    return re.sub(r"-+", "-", value) or "item"


def page_language(text: str) -> str:
    m = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)', text, flags=re.I)
    return (m.group(1) if m else "vi").lower()


def ui_for(language: str) -> dict:
    base = language.split("-")[0]
    return LANG_UI.get(base, LANG_UI["en"])


def page_root(path: Path) -> str:
    rel = path.relative_to(SITE)
    if rel.as_posix() == "404.html":
        suffix = CFG["project"]["canonical_url"].split("/", 3)[-1].strip("/")
        return f"/{suffix}/" if suffix else "/"
    return "../" * (len(rel.parts) - 1)


def source_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            title = re.sub(r"^\d+\s*[·.:\-]\s*", "", title)
            title = title.replace("**", "").strip()
            return title
    return path.stem.replace("_", " ")


def add_theory_anchors() -> list[dict]:
    theory = SITE / "theory.html"
    text = theory.read_text(encoding="utf-8") if theory.exists() else ""
    entries = []
    for path in sorted((ROOT / "content").glob("*.md")):
        if path.name == "00_README_FIRST.md":
            continue
        anchor = "doc-" + slug(path.stem)
        needle = f'<section data-source="{html.escape(path.name)}">'
        replacement = f'<section id="{anchor}" data-source="{html.escape(path.name)}">'
        if needle in text and f'id="{anchor}"' not in text:
            text = text.replace(needle, replacement, 1)
        entries.append({
            "type":"theory-chapter",
            "id": path.stem,
            "title": source_title(path),
            "url": f"theory.html#{anchor}",
            "status":"public chapter",
            "meta": path.name,
        })
    if theory.exists():
        theory.write_text(text, encoding="utf-8")
    return entries


def scientific_index() -> dict:
    chapters = add_theory_anchors()
    claim_entries = []
    for claim in CLAIMS.get("claims", []):
        cid = claim.get("id", "")
        claim_entries.append({
            "type":"claim","id":cid,"title":claim.get("title", cid),
            "url":f"claims/{cid}/","status":claim.get("status", ""),
            "meta":claim.get("type", ""),
        })
    asset_entries = []
    for asset in ASSETS.get("assets", []):
        code = asset.get("code", "")
        asset_entries.append({
            "type":"asset","id":code,"title":asset.get("name", code),
            "url":f"assets/{slug(code)}/","status":asset.get("status", ""),
            "meta":asset.get("kind", ""),
        })

    core_candidates = [
        ("index.html","BL∞ - Tổng quan","overview"),
        ("theory.html","Học thuyết canonical BL∞","theory"),
        ("regressor-proposition.html","Mệnh đề Kẻ Hồi Quy - BL-RP-FRC","research proposition"),
        ("system.html","BL Conservation System","system"),
        ("unknown.html","UNKNOWN Doctrine","doctrine"),
        ("grand-ending.html","Grand Ending","research object"),
        ("world.html","World / narrative research projection","research projection"),
        ("academic-democracy.html","Dân chủ Học thuật","research manifesto"),
        ("open-academic-publishing.html","Open Academic Publishing","technology"),
        ("bl-adn.html","BL-ADN","provenance protocol"),
    ]
    core = [
        {"type":"core","id":url,"title":title,"url":url,"status":"public","meta":kind}
        for url, title, kind in core_candidates if (SITE / url).exists()
    ]

    narrative_candidates = [
        ("novel/","Bách Lâm - Lần Hồi Quy Thứ Một Triệu","serial fiction"),
        ("novel/chapter-001.html","Chương 1 - HALF-CANON","half-canon"),
        ("novel/world-chapter-001.html","World Guide - Chương 1","world guide"),
    ]
    narrative = [
        {"type":"narrative","id":url,"title":title,"url":url,"status":"public","meta":kind}
        for url, title, kind in narrative_candidates if (SITE / url.rstrip("/") / "index.html").exists() or (SITE / url).exists()
    ]

    verification_candidates = [
        ("author.html","Tác giả - Lâm Kim Bách","author"),
        ("provenance.html","Provenance","verification"),
        ("critique.html","Giao thức phản biện","critique"),
        ("languages.html","Ngôn ngữ và phạm vi bản dịch","language hub"),
        ("claims.html","Claim Registry","registry"),
        ("assets.html","Asset Registry","registry"),
        ("machine.html","Machine Layer","machine index"),
    ]
    verification = [
        {"type":"verification","id":url,"title":title,"url":url,"status":"public","meta":kind}
        for url, title, kind in verification_candidates if (SITE / url).exists()
    ]

    machine_candidates = [
        ("machine/manifest.json","Machine manifest"),
        ("machine/claim-index.json","Claim index JSON"),
        ("machine/asset-index.json","Asset index JSON"),
        ("machine/claim-graph.jsonld","Claim graph JSON-LD"),
        ("machine/historical-graph.jsonld","Historical graph JSON-LD"),
        ("machine/bl-infinity-unified-system.json","Unified system contract"),
        ("llms.txt","LLM discovery surface"),
    ]
    machine = [
        {"type":"machine","id":url,"title":title,"url":url,"status":"machine-readable","meta":"public contract"}
        for url, title in machine_candidates if (SITE / url).exists()
    ]

    language_entries = [
        {"type":"language","id":"vi","title":"Tiếng Việt","url":"theory.html","status":"canonical","meta":"full canonical public reading source"},
        {"type":"language","id":"en","title":"English","url":"en/theory.html","status":"core","meta":"core research edition"},
    ]
    for item in TINDEX.get("discovery_editions", {}).get("languages", {}).values():
        if item.get("hreflang") == "en":
            continue
        language_entries.append({
            "type":"language","id":item.get("hreflang", ""),"title":item.get("name", ""),
            "url":item.get("route", ""),"status":"discovery draft","meta":item.get("coverage", "localized summary"),
        })

    groups = [
        {"id":"core","title":"Core research routes","entries":core},
        {"id":"theory","title":"Theory chapters","entries":chapters},
        {"id":"claims","title":"Claim Registry","entries":claim_entries},
        {"id":"assets","title":"Asset Registry","entries":asset_entries},
        {"id":"narrative","title":"Narrative / HALF-CANON","entries":narrative},
        {"id":"verification","title":"Verification and governance","entries":verification},
        {"id":"machine","title":"Machine-readable layer","entries":machine},
        {"id":"languages","title":"Languages","entries":language_entries},
    ]
    return {
        "schema_version":"1.0",
        "namespace":"BL∞",
        "generated_from":"canonical source registries",
        "counts":{g["id"]:len(g["entries"]) for g in groups},
        "groups":groups,
    }


def inject_topic_bar(path: Path, text: str) -> str:
    if 'class="top"' not in text or 'class="topic-bar"' in text or path.name == "404.html":
        return text
    root = page_root(path)
    rel = path.relative_to(SITE).as_posix()
    language = page_language(text)
    ui = ui_for(language)
    routes = [
        ("overview", "index.html"),
        ("theory", "theory.html"),
        ("regressor", "regressor-proposition.html"),
        ("system", "system.html"),
        ("academic", "academic-democracy.html"),
        ("novel", "novel/"),
        ("claims", "claims.html"),
        ("critique", "critique.html"),
    ]
    links = []
    for key, route in routes:
        target_path = SITE / route
        exists = target_path.exists() or (route.endswith("/") and (target_path / "index.html").exists())
        if not exists:
            continue
        current = False
        if key == "overview": current = rel in {"index.html","en/index.html"}
        elif key == "theory": current = rel in {"theory.html","en/theory.html"}
        elif key == "regressor": current = rel == "regressor-proposition.html"
        elif key == "system": current = rel == "system.html"
        elif key == "academic": current = rel == "academic-democracy.html" or rel.startswith("academic-democracy/")
        elif key == "novel": current = rel.startswith("novel/")
        elif key == "claims": current = rel == "claims.html" or rel.startswith("claims/")
        elif key == "critique": current = rel == "critique.html"
        attrs = ' aria-current="page"' if current else ""
        links.append(f'<a href="{html.escape(root + route, quote=True)}" data-topic="{key}"{attrs}>{html.escape(ui[key])}</a>')
    bar = f'<nav class="topic-bar" aria-label="{html.escape(ui["aria"], quote=True)}"><div class="topic-bar-inner">{"".join(links)}</div></nav>'
    return text.replace("</header>", "</header>" + bar, 1)


def inject_assets(path: Path, text: str) -> str:
    if path.name == "404.html":
        return text
    root = page_root(path)
    css_href = root + "assets/css/navigation-system.css"
    js_src = root + "assets/js/navigation-system.js"
    if "navigation-system.css" not in text:
        text = text.replace("</head>", f'<link rel="stylesheet" href="{html.escape(css_href, quote=True)}"></head>', 1)
    if "navigation-system.js" not in text:
        text = text.replace("</body>", f'<script src="{html.escape(js_src, quote=True)}"></script></body>', 1)
    return text


def update_manifest() -> None:
    path = SITE / "machine/manifest.json"
    if not path.exists(): return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scientific_index"] = "scientific-index.json"
    data["navigation_system"] = "../assets/js/navigation-system.js"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_llms() -> None:
    path = SITE / "llms.txt"
    if not path.exists(): return
    text = path.read_text(encoding="utf-8")
    root_url = CFG["project"]["canonical_url"].rstrip("/") + "/"
    marker = "Scientific navigation index:"
    if marker not in text:
        text += f"\n\n{marker} {root_url}machine/scientific-index.json\n"
        text += "Navigation policy: browser language is prioritized when a matching public edition exists; translation scope labels remain authoritative.\n"
        path.write_text(text, encoding="utf-8")


def main() -> None:
    if not SITE.exists():
        raise SystemExit("site/ missing")
    (SITE / "assets/css").mkdir(parents=True, exist_ok=True)
    (SITE / "assets/js").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "assets/css/navigation-system.css", SITE / "assets/css/navigation-system.css")
    shutil.copy(ROOT / "assets/js/navigation-system.js", SITE / "assets/js/navigation-system.js")

    idx = scientific_index()
    (SITE / "machine").mkdir(parents=True, exist_ok=True)
    (SITE / "machine/scientific-index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

    changed = 0
    for path in SITE.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        revised = inject_topic_bar(path, original)
        revised = inject_assets(path, revised)
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            changed += 1
    update_manifest()
    update_llms()
    print(f"Navigation system built: {changed} HTML pages; scientific index groups={len(idx['groups'])}")


if __name__ == "__main__":
    main()
