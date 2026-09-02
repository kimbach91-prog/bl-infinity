from pathlib import Path
import json
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

TOPIC_ORDER = ["overview", "theory", "novel", "regressor", "system", "academic", "claims", "critique"]
HOME_ORDER = [
    "theory.html", "novel/", "regressor-proposition.html", "system.html",
    "academic-democracy.html", "open-academic-publishing.html", "unknown.html",
    "grand-ending.html", "world.html", "bl-adn.html", "claims.html", "assets.html",
    "provenance.html", "critique.html", "author.html", "languages.html", "machine.html",
    "academic-democracy-technology.html", "academic-democracy/discovery.html",
]
GROUP_ORDER = ["core", "theory", "narrative", "claims", "assets", "verification", "machine", "languages"]
HEADING_RE = re.compile(r'<h([1-6])(\b[^>]*)>(.*?)</h\1>', flags=re.I | re.S)


def normalize(text: str) -> str:
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


def reorder_scientific_index() -> None:
    path = SITE / "machine" / "scientific-index.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    rank = {group_id: index for index, group_id in enumerate(GROUP_ORDER)}
    data["groups"] = sorted(data.get("groups", []), key=lambda group: rank.get(group.get("id", ""), 999))
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


def verify_navigation_hierarchy() -> None:
    checked = 0
    for path in SITE.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        topic_match = re.search(r'<div class="topic-bar-inner">(.*?)</div>', text, flags=re.S)
        if topic_match:
            found = re.findall(r'\bdata-topic="([^"]+)"', topic_match.group(1))
            expected = [key for key in TOPIC_ORDER if key in found]
            if found != expected:
                raise RuntimeError(f"topic hierarchy mismatch in {path.relative_to(SITE)}: {found}")
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

    index_path = SITE / "machine" / "scientific-index.json"
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        groups = [group.get("id") for group in data.get("groups", [])]
        if "theory" in groups and "narrative" in groups and groups.index("narrative") != groups.index("theory") + 1:
            raise RuntimeError(f"Scientific Index theory/narrative adjacency lost: {groups}")
    print(f"Navigation hierarchy verified across {checked} topic-bar pages")


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

    hierarchy_changed = 0
    for path in SITE.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        revised = normalize_heading_hierarchy(reorder_home_directory(reorder_topic_bar(original)))
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            hierarchy_changed += 1
    reorder_scientific_index()
    verify_navigation_hierarchy()
    verify_heading_hierarchy()
    print(f"Static navigation and heading hierarchy finalized: {hierarchy_changed} HTML files changed")


if __name__ == "__main__":
    main()
