from pathlib import Path
import json
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

# Public hierarchy invariant: BL∞ theory is the first scientific entry surface.
# Novel stays immediately adjacent, separated only by the infinity bridge.
TOPIC_ORDER = ["theory", "novel", "regressor", "system", "academic", "claims", "critique", "overview"]
HOME_ORDER = [
    "theory.html", "novel/", "regressor-proposition.html", "unknown.html",
    "grand-ending.html", "system.html", "world.html", "science-constellation.html",
    "academic-democracy.html", "open-academic-publishing.html", "bl-adn.html",
    "claims.html", "assets.html", "provenance.html", "critique.html", "author.html",
    "languages.html", "machine.html", "academic-democracy-technology.html",
    "academic-democracy/discovery.html", "index.html",
]
GROUP_ORDER = ["core", "theory", "narrative", "external-science", "claims", "assets", "verification", "machine", "languages"]
CORE_ORDER = [
    "theory.html", "regressor-proposition.html", "unknown.html", "grand-ending.html",
    "system.html", "world.html", "index.html", "academic-democracy.html",
    "open-academic-publishing.html", "bl-adn.html",
]
HEADING_RE = re.compile(r'<h([1-6])(\b[^>]*)>(.*?)</h\1>', flags=re.I | re.S)
INFINITY_BRIDGE = '<span class="lineage-infinity-separator" aria-hidden="true" title="∞">∞</span>'
UNPUBLISHED_ROLE_TERMS = ["Kẻ hề", "kẻ hề", "Kẻ thắng", "kẻ thắng", "Kẻ trung gian", "kẻ trung gian", "Kẻ quan sát", "Kẻ đứng ngoài"]


def normalize(text: str) -> str:
    # Public narrative can discuss scientific reversals, but working names for
    # the unpublished BL role-theory stay out of rendered website surfaces.
    text = text.replace("Kẻ thắng hôm nay, kẻ hề ngày mai", "Lịch sử đảo chiều của khoa học")
    text = text.replace("“Kẻ thắng” không chết", "Một framework đang thắng không nhất thiết chết")
    text = text.replace("\"Kẻ thắng\" không chết", "Một framework đang thắng không nhất thiết chết")
    text = text.replace(" — ", ": ")
    text = text.replace("—", ", ")
    text = text.replace(" – ", " · ")
    text = text.replace("–", "-")
    return text


def normalize_heading_hierarchy(text: str) -> str:
    """Repair only rendered HTML heading levels; do not rewrite canonical source text."""
    out = []
    cursor = 0
    previous_level = None
    for match in HEADING_RE.finditer(text):
        level = int(match.group(1))
        repaired = level
        if previous_level is not None and level > previous_level + 1:
            repaired = previous_level + 1
        out.append(text[cursor:match.start()])
        out.append(f'<h{repaired}{match.group(2)}>{match.group(3)}</h{repaired}>')
        cursor = match.end()
        previous_level = repaired
    out.append(text[cursor:])
    return "".join(out)


def reorder_topic_bar(text: str) -> str:
    pattern = re.compile(r'(<div class="topic-bar-inner">)(.*?)(</div>)', re.S)

    def replace(match: re.Match) -> str:
        body = match.group(2)
        links = re.findall(r'<a\b[^>]*\bdata-topic="([^"]+)"[^>]*>.*?</a>', body, flags=re.S)
        if not links:
            return match.group(0)
        blocks = re.findall(r'<a\b[^>]*\bdata-topic="[^"]+"[^>]*>.*?</a>', body, flags=re.S)
        by_key = {}
        unknown = []
        for block in blocks:
            key_match = re.search(r'\bdata-topic="([^"]+)"', block)
            key = key_match.group(1) if key_match else ""
            if key and key not in by_key:
                by_key[key] = block
            else:
                unknown.append(block)
        ordered = [by_key[key] for key in TOPIC_ORDER if key in by_key]
        ordered.extend(block for key, block in by_key.items() if key not in TOPIC_ORDER)
        ordered.extend(unknown)
        return match.group(1) + "".join(ordered) + match.group(3)

    return pattern.sub(replace, text, count=1)


def insert_infinity_bridge(text: str) -> str:
    """Render Học thuyết ∞ Tiểu thuyết / Theory ∞ Novel without merging their identities."""
    def bridge_between(value: str, attribute: str, left: str, right: str) -> str:
        pattern = re.compile(
            rf'(<a\b(?=[^>]*\b{re.escape(attribute)}="{re.escape(left)}")[^>]*>.*?</a>)\s*'
            rf'(?:<span class="lineage-infinity-separator"[^>]*>∞</span>\s*)?'
            rf'(<a\b(?=[^>]*\b{re.escape(attribute)}="{re.escape(right)}")[^>]*>.*?</a>)',
            flags=re.I | re.S,
        )
        return pattern.sub(lambda m: m.group(1) + INFINITY_BRIDGE + m.group(2), value, count=1)

    text = bridge_between(text, "data-section", "theory", "novel")
    text = bridge_between(text, "data-topic", "theory", "novel")
    return text


def home_route(item: str) -> str:
    match = re.search(r'<a\s+href="([^"]+)"', item)
    if not match:
        return ""
    route = match.group(1).split("#", 1)[0].split("?", 1)[0].lstrip("./")
    if route == "novel/index.html":
        route = "novel/"
    return route


def add_reading_pair_class(item: str) -> str:
    if "bl-reading-pair" in item:
        return item
    if re.match(r'<li\b[^>]*\bclass="', item):
        return re.sub(r'(<li\b[^>]*\bclass=")([^"]*)', r'\1\2 bl-reading-pair', item, count=1)
    return item.replace("<li", '<li class="bl-reading-pair"', 1)


def reorder_home_directory(text: str) -> str:
    pattern = re.compile(r'(<ul class="home-directory-grid">)(.*?)(</ul>)', re.S)
    rank = {route: index for index, route in enumerate(HOME_ORDER)}

    def replace(match: re.Match) -> str:
        items = re.findall(r'<li\b[^>]*>.*?</li>', match.group(2), flags=re.S)
        if not items:
            return match.group(0)
        items.sort(key=lambda item: rank.get(home_route(item), 999))
        for index in range(min(2, len(items))):
            if home_route(items[index]) in {"theory.html", "novel/"}:
                items[index] = add_reading_pair_class(items[index])
        return match.group(1) + "".join(items) + match.group(3)

    return pattern.sub(replace, text, count=1)


def science_anchor(domain: str, node_id: str) -> str:
    d = (domain or "").lower()
    if node_id in {"EXT-NEG-LK99", "EXT-NEG-OPERA"}:
        return "turnovers"
    if any(token in d for token in ["particle", "quantum", "gravitation", "astronomy", "cosmology"]):
        return "physics"
    if any(token in d for token in ["earth", "climate", "genom", "biology", "neuro", "medicine", "microbiology"]):
        return "earth-life"
    if any(token in d for token in ["material", "chemistry", "computer", "artificial intelligence", "statistical physics"]):
        return "materials-compute"
    return "compiler"


def enrich_external_science_index() -> None:
    index_path = SITE / "machine" / "scientific-index.json"
    registry_path = SITE / "machine" / "external-science-constellation.json"
    if not index_path.exists() or not registry_path.exists():
        return
    data = json.loads(index_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("lineage_policy") != "EXTERNAL_SCIENCE_REMAINS_OUTSIDE_BL_GENEALOGY":
        raise RuntimeError("external science lineage boundary missing")

    entries = [{
        "type": "external-science-atlas",
        "id": registry.get("object_id", "EXT-SCI-CONSTELLATION-v1"),
        "title": registry.get("title", "External Science Constellation"),
        "url": "science-constellation.html",
        "status": "public curated atlas",
        "meta": "outside BL genealogy",
    }]
    for node in registry.get("nodes", []):
        node_id = node.get("id", "")
        entries.append({
            "type": "external-science",
            "id": node_id,
            "title": node.get("title", node_id),
            "url": f"science-constellation.html#{science_anchor(node.get('domain', ''), node_id)}",
            "status": node.get("status", ""),
            "meta": f"{node.get('domain', '')} · outside BL genealogy",
        })

    group = {
        "id": "external-science",
        "title": "External science / outside BL genealogy",
        "entries": entries,
    }
    groups = [g for g in data.get("groups", []) if g.get("id") != "external-science"]
    groups.append(group)
    data["groups"] = groups
    counts = data.setdefault("counts", {})
    counts["external-science"] = len(entries)
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def reorder_scientific_index() -> None:
    path = SITE / "machine" / "scientific-index.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    rank = {group_id: index for index, group_id in enumerate(GROUP_ORDER)}
    data["groups"] = sorted(data.get("groups", []), key=lambda group: rank.get(group.get("id", ""), 999))

    core_rank = {route: index for index, route in enumerate(CORE_ORDER)}
    for group in data.get("groups", []):
        if group.get("id") != "core":
            continue
        group["title"] = "BL∞ core / Học thuyết và các nhánh trực tiếp"
        group["entries"] = sorted(
            group.get("entries", []),
            key=lambda entry: core_rank.get(entry.get("url", ""), 999),
        )

    data["counts"] = {group.get("id", "unknown"): len(group.get("entries", [])) for group in data.get("groups", [])}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verify_heading_hierarchy() -> None:
    checked = 0
    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        levels = [int(match.group(1)) for match in HEADING_RE.finditer(text)]
        for previous, current in zip(levels, levels[1:]):
            if current > previous + 1:
                raise RuntimeError(
                    f"heading hierarchy jump in {path.relative_to(SITE)}: h{previous} -> h{current}"
                )
        checked += 1
    print(f"Heading hierarchy verified across {checked} HTML pages")


def verify_unpublished_role_boundary() -> None:
    leaks = []
    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for term in UNPUBLISHED_ROLE_TERMS:
            if term in text:
                leaks.append(f"{path.relative_to(SITE)}:{term}")
    if leaks:
        raise RuntimeError("unpublished BL role names leaked to public HTML: " + ", ".join(leaks[:20]))
    print("Unpublished BL role-name boundary: public HTML clean")


def verify_infinity_bridge(text: str, path: Path) -> None:
    for attribute, left, right in [("data-section", "theory", "novel"), ("data-topic", "theory", "novel")]:
        if f'{attribute}="{left}"' not in text or f'{attribute}="{right}"' not in text:
            continue
        pattern = re.compile(
            rf'<a\b(?=[^>]*\b{attribute}="{left}")[^>]*>.*?</a>'
            rf'<span class="lineage-infinity-separator"[^>]*>∞</span>'
            rf'<a\b(?=[^>]*\b{attribute}="{right}")[^>]*>.*?</a>',
            flags=re.I | re.S,
        )
        if not pattern.search(text):
            raise RuntimeError(f"infinity bridge missing in {path.relative_to(SITE)} for {attribute}")


def verify_navigation_hierarchy() -> None:
    checked = 0
    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        verify_infinity_bridge(text, path)
        topic_match = re.search(r'<div class="topic-bar-inner">(.*?)</div>', text, flags=re.S)
        if topic_match:
            found = re.findall(r'\bdata-topic="([^"]+)"', topic_match.group(1))
            expected = [key for key in TOPIC_ORDER if key in found]
            if found != expected:
                raise RuntimeError(f"topic hierarchy mismatch in {path.relative_to(SITE)}: {found}")
            if "theory" in found and found[0] != "theory":
                raise RuntimeError(f"theory must be first in topic hierarchy: {path.relative_to(SITE)}")
            if "theory" in found and "novel" in found and found.index("novel") != found.index("theory") + 1:
                raise RuntimeError(f"theory/novel adjacency lost in {path.relative_to(SITE)}")
            checked += 1

    home = SITE / "index.html"
    if home.exists():
        text = home.read_text(encoding="utf-8")
        match = re.search(r'<ul class="home-directory-grid">(.*?)</ul>', text, flags=re.S)
        if match:
            items = re.findall(r'<li\b[^>]*>.*?</li>', match.group(1), flags=re.S)
            first_routes = [home_route(item) for item in items[:2]]
            if first_routes != ["theory.html", "novel/"]:
                raise RuntimeError(f"homepage reading pair mismatch: {first_routes}")
            routes = [home_route(item) for item in items]
            expected_prefix = [
                "theory.html", "novel/", "regressor-proposition.html", "unknown.html",
                "grand-ending.html", "system.html", "world.html", "science-constellation.html",
            ]
            actual_prefix = [route for route in routes if route in expected_prefix][:len(expected_prefix)]
            if actual_prefix != expected_prefix:
                raise RuntimeError(f"BL∞ core homepage hierarchy mismatch: {actual_prefix}")

    index_path = SITE / "machine" / "scientific-index.json"
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        groups = [group.get("id") for group in data.get("groups", [])]
        if not groups or groups[0] != "core":
            raise RuntimeError(f"BL∞ core group must be first in Scientific Index: {groups}")
        core = next((group for group in data.get("groups", []) if group.get("id") == "core"), None)
        if core and core.get("entries"):
            first_core = core["entries"][0].get("url")
            if first_core != "theory.html":
                raise RuntimeError(f"canonical BL∞ theory must be first core entry: {first_core}")
        if "theory" in groups and "narrative" in groups and groups.index("narrative") != groups.index("theory") + 1:
            raise RuntimeError(f"Scientific Index theory/narrative adjacency lost: {groups}")
        if "external-science" not in groups:
            raise RuntimeError("Scientific Index external-science group missing")
        if groups.index("external-science") != groups.index("narrative") + 1:
            raise RuntimeError(f"External science group must follow narrative/world layer: {groups}")
    print(f"Theory-first BL∞ hierarchy verified across {checked} topic-bar pages")


def main() -> None:
    changed = 0
    for path in SITE.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        revised = normalize(original)
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            changed += 1
        if "—" in revised or "–" in revised:
            raise RuntimeError(f"long dash remains in {path.relative_to(SITE)}")
    print(f"Human-facing typography normalized: {changed} HTML files changed")

    navigation_builder = ROOT / "scripts" / "build_navigation_system.py"
    runpy.run_path(str(navigation_builder), run_name="__main__")

    enrich_external_science_index()
    hierarchy_changed = 0
    for path in SITE.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        revised = normalize_heading_hierarchy(
            insert_infinity_bridge(reorder_home_directory(reorder_topic_bar(original)))
        )
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            hierarchy_changed += 1
    reorder_scientific_index()
    verify_navigation_hierarchy()
    verify_heading_hierarchy()
    verify_unpublished_role_boundary()
    print(f"Theory-first BL∞ hierarchy, infinity bridge, external science lineage and heading hierarchy finalized: {hierarchy_changed} HTML files changed")


if __name__ == "__main__":
    main()
