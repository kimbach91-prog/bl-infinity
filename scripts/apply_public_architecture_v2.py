from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ARCH_SOURCE = ROOT / "machine" / "public-architecture.json"
HYP_SOURCE_ID = "52_COMPRESSED_SUPERENTITY_MILLION_REGRESSION_HYPOTHESIS"
SEP = '<span class="lineage-infinity-separator" aria-hidden="true" title="∞">∞</span>'


def home_route(item: str) -> str:
    m = re.search(r'<a\s+href="([^"]+)"', item)
    if not m:
        return ""
    route = m.group(1).split("#", 1)[0].split("?", 1)[0].lstrip("./")
    return "novel/" if route == "novel/index.html" else route


def patch_homepage() -> None:
    path = SITE / "index.html"
    text = path.read_text(encoding="utf-8")

    # BL∞ is the containing field, not a self-referential peer card.
    text = re.sub(r'<li class="bl-infinity-root-entry">.*?</li>', "", text, count=1, flags=re.S)
    text = text.replace(
        '<strong>Học thuyết UNKNOWN · Trường Chưa-biết Sinh thành của BL∞</strong>',
        '<strong>UNKNOWN · Biên Chưa-biết Sinh thành của BL∞</strong>',
    )

    if 'id="bl-infinity-field-map"' not in text:
        marker = '<ul class="home-directory-grid">'
        if marker not in text:
            raise RuntimeError("homepage directory marker missing")
        field_map = f'''<section class="bl-infinity-field-map" id="bl-infinity-field-map" aria-labelledby="bl-field-title">
<p class="eyebrow">BL∞ · AMBIENT GENERATIVE FIELD</p>
<h2 id="bl-field-title">BL∞ là trường bao của toàn public projection này</h2>
<p>BL∞ không phải một node hoặc card ngang hàng với các nhánh bên dưới. Mỗi trang chỉ là một hiện thân hữu hạn trong trường mở; Reality, mô hình, giả thuyết, truyện, hệ thống, phả hệ và khoa học ngoài BL giữ loại quan hệ riêng.</p>
<div class="bl-primary-surface-chain"><a href="theory.html">Học thuyết</a>{SEP}<a href="hypotheses.html">Giả thuyết</a>{SEP}<a href="novel/">Tiểu thuyết</a></div>
<div class="bl-boundary-planes"><a href="theory.html#doc-46_reality_gia_tai_dual_propositions"><strong>Reality</strong><small>actuality / relation boundary</small></a><span class="bl-l-infinity-hold"><strong>L∞</strong><small>design pillar preserved · definition recovery HOLD</small></span></div>
<p class="bl-field-law"><code>BL∞ → Reality Relation Space → Reality Veto → Model / Decision / Action → Outcome → Expanded BL∞ Frontier</code></p>
</section>'''
        text = text.replace(marker, field_map + marker, 1)

    pattern = re.compile(r'(<ul class="home-directory-grid">)(.*?)(</ul>)', re.S)
    order = [
        "theory.html", "hypotheses.html", "novel/", "regressor-proposition.html",
        "unknown.html", "grand-ending.html", "system.html", "world.html",
        "science-constellation.html", "mature-theory-synthesis.html",
    ]
    rank = {route: index for index, route in enumerate(order)}

    def reorder(match: re.Match) -> str:
        items = re.findall(r'<li\b[^>]*>.*?</li>', match.group(2), flags=re.S)
        items.sort(key=lambda item: rank.get(home_route(item), 999))
        return match.group(1) + "".join(items) + match.group(3)

    text = pattern.sub(reorder, text, count=1)
    path.write_text(text, encoding="utf-8")


def patch_navigation() -> None:
    for path in SITE.rglob("*.html"):
        if path.name == "404.html":
            continue
        text = path.read_text(encoding="utf-8")
        # The BL∞ brand is the overview projection; Overview is not a peer topic.
        text = re.sub(
            r'<a\b(?=[^>]*\bdata-topic="overview")[^>]*>.*?</a>',
            "",
            text,
            count=1,
            flags=re.I | re.S,
        )
        path.write_text(text, encoding="utf-8")


def patch_scientific_index() -> None:
    path = SITE / "machine" / "scientific-index.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    architecture = json.loads(ARCH_SOURCE.read_text(encoding="utf-8"))
    data["architecture"] = architecture

    groups = []
    direct = None
    for group in data.get("groups", []):
        gid = group.get("id")
        if gid == "core":
            entries = [
                entry for entry in group.get("entries", [])
                if entry.get("url") not in {"index.html", "theory.html", "hypotheses.html"}
            ]
            for entry in entries:
                if entry.get("url") == "unknown.html":
                    entry["title"] = "UNKNOWN · epistemic frontier / doctrine"
            direct = {
                "id": "bl-direct-branches",
                "title": "BL∞ finite direct branches / systems / governance",
                "entries": entries,
            }
            continue
        if gid == "theory":
            group["entries"] = [
                entry for entry in group.get("entries", [])
                if entry.get("id") != HYP_SOURCE_ID
            ]
        groups.append(group)

    if direct:
        groups.append(direct)

    order = [
        "theory", "hypotheses", "narrative", "bl-direct-branches",
        "external-science", "mature-theory-synthesis", "claims", "assets",
        "verification", "machine", "languages",
    ]
    rank = {gid: index for index, gid in enumerate(order)}
    groups.sort(key=lambda group: rank.get(group.get("id", ""), 999))
    data["groups"] = groups
    data["counts"] = {group["id"]: len(group.get("entries", [])) for group in groups}
    data["reclassifications"] = [{
        "source_id": HYP_SOURCE_ID,
        "from": "theory-index",
        "to": "hypothesis-branch",
        "reason": "explicit hypothesis object; Theory != Hypothesis",
    }]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_machine_contracts() -> None:
    machine = SITE / "machine"
    machine.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ARCH_SOURCE, machine / "public-architecture.json")

    mts_path = machine / "bl-mature-theory-synthesis.json"
    weave_path = machine / "novel-global-science-weave.json"
    if mts_path.exists() and weave_path.exists():
        mts = json.loads(mts_path.read_text(encoding="utf-8"))
        weave = json.loads(weave_path.read_text(encoding="utf-8"))
        coverage = {
            "id": "BL-NOVEL-SCIENCE-COVERAGE",
            "status": "PARTIAL_EXPLICIT_WEAVE_WITH_OPEN_CONTINUITY_POOL",
            "explicit_chapter_001_historical_anchors": len(weave.get("chapter_001_montage", [])),
            "mature_theory_families_available_as_continuity_constraints": len(mts.get("theory_families", [])),
            "not_claimed": "all mature science has already appeared as narrative scenes",
            "rule": "availability_as_constraint != already_woven_into_scene",
        }
        (machine / "novel-science-coverage.json").write_text(
            json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    manifest_path = machine / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["public_architecture"] = "public-architecture.json"
        manifest["novel_science_coverage"] = "novel-science-coverage.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_css() -> None:
    path = SITE / "assets" / "css" / "navigation-system.css"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "/* BL∞ field architecture v2 */"
    if marker in text:
        return
    text += '''
/* BL∞ field architecture v2 */
.bl-infinity-field-map{margin:22px 0 28px;padding:clamp(20px,4vw,34px);border:1px solid rgba(125,21,21,.28);border-radius:24px;background:linear-gradient(145deg,var(--accent-soft),#fff 58%);box-shadow:0 14px 42px rgba(32,18,18,.06)}
.bl-infinity-field-map h2{max-width:18ch;margin:.2em 0 .35em;font-size:clamp(2rem,4.8vw,4rem);letter-spacing:-.045em}
.bl-primary-surface-chain{display:flex;align-items:center;gap:9px;overflow-x:auto;margin:22px 0 15px;padding:4px 0}
.bl-primary-surface-chain a{flex:0 0 auto;padding:11px 15px;border:1px solid rgba(125,21,21,.25);border-radius:999px;background:#fff;color:var(--accent);font-weight:900;text-decoration:none}
.bl-boundary-planes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:14px 0}
.bl-boundary-planes>a,.bl-l-infinity-hold{display:flex;flex-direction:column;gap:3px;padding:13px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.78);color:var(--ink);text-decoration:none}
.bl-boundary-planes small{color:var(--muted)}
.bl-l-infinity-hold{border-style:dashed}
.bl-field-law{margin:16px 0 0;overflow:auto}.bl-field-law code{white-space:nowrap}
@media(max-width:620px){.bl-boundary-planes{grid-template-columns:1fr}}
'''
    path.write_text(text, encoding="utf-8")


def verify() -> None:
    home = (SITE / "index.html").read_text(encoding="utf-8")
    if 'class="bl-infinity-root-entry"' in home:
        raise RuntimeError("BL∞ still represented as a peer/self-card")
    if 'id="bl-infinity-field-map"' not in home:
        raise RuntimeError("BL∞ ambient field map missing")
    if "Học thuyết UNKNOWN" in home:
        raise RuntimeError("UNKNOWN still misclassified as theory on homepage")

    directory = re.search(r'<ul class="home-directory-grid">(.*?)</ul>', home, re.S)
    items = re.findall(r'<li\b[^>]*>.*?</li>', directory.group(1), re.S) if directory else []
    first_routes = [home_route(item) for item in items[:3]]
    if first_routes != ["theory.html", "hypotheses.html", "novel/"]:
        raise RuntimeError(f"finite public surfaces not theory-first: {first_routes}")

    for path in SITE.rglob("*.html"):
        if path.name == "404.html":
            continue
        if 'data-topic="overview"' in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"Overview still represented as peer topic: {path.relative_to(SITE)}")

    index = json.loads((SITE / "machine" / "scientific-index.json").read_text(encoding="utf-8"))
    groups = [group.get("id") for group in index.get("groups", [])]
    if groups[:4] != ["theory", "hypotheses", "narrative", "bl-direct-branches"]:
        raise RuntimeError(f"Scientific Index field topology mismatch: {groups[:4]}")
    if not index.get("architecture", {}).get("ambient_field", {}).get("not_a_peer_node"):
        raise RuntimeError("Scientific Index lost BL∞ ambient-field semantics")
    theory = index["groups"][0]
    if any(entry.get("id") == HYP_SOURCE_ID for entry in theory.get("entries", [])):
        raise RuntimeError("explicit hypothesis still present in Theory group")

    coverage_path = SITE / "machine" / "novel-science-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    if coverage.get("explicit_chapter_001_historical_anchors") != 6:
        raise RuntimeError("Chapter 1 science coverage count drift")
    if coverage.get("mature_theory_families_available_as_continuity_constraints", 0) < 40:
        raise RuntimeError("mature-theory continuity pool unexpectedly shrank")

    print(
        "BL∞ field-first architecture verified: "
        f"groups={groups[:6]} theory={len(theory.get('entries', []))} "
        f"chapter1_science={coverage['explicit_chapter_001_historical_anchors']} "
        f"continuity_pool={coverage['mature_theory_families_available_as_continuity_constraints']}"
    )


def main() -> None:
    patch_homepage()
    patch_navigation()
    patch_scientific_index()
    write_machine_contracts()
    patch_css()
    verify()


if __name__ == "__main__":
    main()
