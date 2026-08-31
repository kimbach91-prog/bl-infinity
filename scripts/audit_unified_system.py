from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "machine" / "bl-infinity-unified-system.json"
CONSTITUENTS_PATH = ROOT / "machine" / "unified-constituents.json"
CANONICAL_DOCS = [
    ROOT / "content" / "43_BL_INFINITY_GRAND_UNIFICATION.md",
    ROOT / "content" / "44_CANONICAL_UNIFIED_LOGIC_STACK.md",
    ROOT / "content" / "45_UNIFIED_CONSTITUENT_PROFILES.md",
]

REQUIRED_NODES = {
    "REALITY", "ACTION_OR_TEST", "BL∞",
    "RVT", "RVP", "RVTP", "RVL",
    "BLEE", "Academic-Democracy", "BL-HRD",
    "BL-ADN", "BL-LOG", "BL-CHRONO",
    "BL-PCRO", "BL-OODP", "BLOK", "BL-NOVO",
    "BL-REV", "BL-AEGIS", "BL-SFRET", "OPT-HKRP",
    "OHAS", "KAT", "BL-PIRAL", "SRS", "BL-CPR",
}

REQUIRED_PROFILE_IDS = {
    "RVT", "BLEE", "Academic-Democracy", "KAT",
    "OPT-HKRP", "OHAS", "BL-SFRET", "BL-REV",
}

REQUIRED_EDGES = {
    ("BL∞", "FEEDS", "BL-HRD"),
    ("BLEE", "FORMALIZES", "Academic-Democracy"),
    ("Academic-Democracy", "FEEDS", "BL-HRD"),
    ("BL-HRD", "ROUTES_TO", "BL-ADN"),
    ("BL-HRD", "ROUTES_TO", "BL-PCRO"),
    ("BL-HRD", "ROUTES_TO", "BL-NOVO"),
    ("BL-HRD", "ROUTES_TO", "BL-REV"),
    ("BL-REV", "FEEDS", "BL-AEGIS"),
    ("BL-AEGIS", "PREPARES", "RVTP"),
    ("RVTP", "FEEDS", "RVL"),
    ("BL-SFRET", "PREPARES", "OPT-HKRP"),
    ("OPT-HKRP", "ROUTES_TO", "OHAS"),
    ("OHAS", "AUTHORIZES", "ACTION_OR_TEST"),
    ("ACTION_OR_TEST", "ACTS_ON", "REALITY"),
    ("REALITY", "FEEDS", "RVTP"),
    ("RVL", "FEEDS", "KAT"),
    ("KAT", "CONVERTS", "BL∞"),
    ("BL-CPR", "CONSTRAINS", "BL-INF-UNIFY"),
}

RVP_GOVERNED = {
    "BL∞", "BLEE", "Academic-Democracy", "BL-HRD", "BL-NOVO",
    "BL-REV", "BL-SFRET", "OPT-HKRP", "OHAS", "KAT",
}

FORBIDDEN_PUBLIC_KEYS = {
    "routing_weights", "private_ranking_functions", "activation_triggers",
    "private_diagnostics", "production_router", "operator_playbook",
}


def fail(msg: str) -> None:
    print(f"[BL-INF-UNIFY AUDIT] FAIL: {msg}")
    sys.exit(1)


def load_json(path: Path):
    if not path.exists():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from walk_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_keys(item)


def main() -> None:
    graph = load_json(GRAPH_PATH)
    constituents = load_json(CONSTITUENTS_PATH)

    for doc in CANONICAL_DOCS:
        if not doc.exists():
            fail(f"missing canonical unification document: {doc.relative_to(ROOT)}")

    if graph.get("id") != "BL-INF-UNIFY":
        fail("graph id must be BL-INF-UNIFY")
    if graph.get("truth_authority") != "Reality Veto":
        fail("truth_authority must remain Reality Veto")
    if graph.get("public_projection") is not True:
        fail("unified graph must declare public_projection=true")
    if graph.get("not_runtime_router") is not True:
        fail("unified graph must declare not_runtime_router=true")
    if graph.get("not_identity_collapse") is not True:
        fail("unified graph must declare not_identity_collapse=true")

    node_ids = {n.get("id") for n in graph.get("nodes", [])}
    missing_nodes = REQUIRED_NODES - node_ids
    if missing_nodes:
        fail(f"missing required nodes: {sorted(missing_nodes)}")

    relation_types = set(graph.get("relation_types", []))
    edges = graph.get("edges", [])
    edge_set = set()
    for edge in edges:
        src, typ, dst = edge.get("from"), edge.get("type"), edge.get("to")
        if typ not in relation_types:
            fail(f"edge uses undeclared relation type: {src} -[{typ}]-> {dst}")
        if src not in node_ids and src != "BL-INF-UNIFY":
            fail(f"edge source does not exist: {src}")
        if dst not in node_ids and dst != "BL-INF-UNIFY":
            fail(f"edge target does not exist: {dst}")
        edge_set.add((src, typ, dst))

    missing_edges = REQUIRED_EDGES - edge_set
    if missing_edges:
        fail(f"missing required integration edges: {sorted(missing_edges)}")

    for node in RVP_GOVERNED:
        if ("RVP", "GOVERNS", node) not in edge_set:
            fail(f"Reality Veto governance edge missing for {node}")

    if ("OHAS", "GOVERNS", "REALITY") in edge_set or ("OHAS", "CONSTRAINS", "REALITY") in edge_set:
        fail("OHAS must never be modeled as governing/constraining REALITY")

    cycle = graph.get("canonical_cycle", [])
    if not cycle or cycle[0] != "REALITY":
        fail("canonical cycle must start at REALITY")
    if "ACTION_OR_TEST" not in cycle or "KAT" not in cycle or "BL∞" not in cycle:
        fail("canonical cycle missing action/capability return path")
    for item in cycle:
        if item not in node_ids:
            fail(f"canonical cycle references unknown node: {item}")

    progress = graph.get("progress_condition", "").lower()
    if "delta" not in progress:
        fail("progress_condition must require an inspectable delta")

    profile_ids = {p.get("id") for p in constituents.get("profiles", [])}
    missing_profiles = REQUIRED_PROFILE_IDS - profile_ids
    if missing_profiles:
        fail(f"missing required constituent profiles: {sorted(missing_profiles)}")

    public_keys = set(walk_keys(graph)) | set(walk_keys(constituents))
    leaked_keys = FORBIDDEN_PUBLIC_KEYS & public_keys
    # These words are allowed only as string values in explicit withheld lists, not as live object keys.
    if leaked_keys:
        fail(f"protected runtime concepts exposed as machine object keys: {sorted(leaked_keys)}")

    print("[BL-INF-UNIFY AUDIT] PASS")
    print(f"nodes={len(node_ids)} edges={len(edges)} profiles={len(profile_ids)}")
    print("Reality Veto sovereignty, identity preservation, action boundary and recursive delta checks passed.")


if __name__ == "__main__":
    main()
