from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "machine" / "bl-infinity-unified-system.json"
TOPOLOGY_PATH = ROOT / "machine" / "reality-gia-tai-topology.json"
CONSTITUENTS_PATH = ROOT / "machine" / "unified-constituents.json"
LOGIC_STACK_PATH = ROOT / "machine" / "logic-stack.json"
CANONICAL_DOCS = [
    ROOT / "content" / "43_BL_INFINITY_GRAND_UNIFICATION.md",
    ROOT / "content" / "44_CANONICAL_UNIFIED_LOGIC_STACK.md",
    ROOT / "content" / "45_UNIFIED_CONSTITUENT_PROFILES.md",
    ROOT / "content" / "46_REALITY_GIA_TAI_DUAL_PROPOSITIONS.md",
    ROOT / "content" / "47_CANONICAL_DYNAMIC_REALITY_GIA_TAI_STACK.md",
]

REQUIRED_NODES = {
    "REALITY", "GIA_TAI", "BL-RP", "BL-GTP", "REALITY_TEST_INTERFACE",
    "ACTION_OR_TEST", "BL∞", "RVT", "RVP", "RVTP", "RVL",
    "BLEE", "Academic-Democracy", "BL-HRD",
    "BL-ADN", "BL-LOG", "BL-CHRONO", "BL-PCRO", "BL-OODP", "BLOK",
    "BL-NOVO", "BL-REV", "BL-AEGIS", "BL-SFRET", "OPT-HKRP",
    "OHAS", "KAT", "BL-PIRAL", "SRS", "BL-CPR",
}

REQUIRED_PROFILE_IDS = {
    "BL-RP", "BL-GTP", "RVT", "BLEE", "Academic-Democracy", "KAT",
    "OPT-HKRP", "OHAS", "BL-SFRET", "BL-REV",
}

REQUIRED_EDGES = {
    ("BL-RP", "FORMALIZES", "REALITY"),
    ("BL-GTP", "FORMALIZES", "GIA_TAI"),
    ("REALITY", "FEEDS", "BL∞"),
    ("BL∞", "GENERATES", "GIA_TAI"),
    ("GIA_TAI", "FEEDS", "BL∞"),
    ("BL∞", "EXPANDS", "REALITY_TEST_INTERFACE"),
    ("GIA_TAI", "ROUTES_TO", "BL-HRD"),
    ("BL-HRD", "ROUTES_TO", "REALITY_TEST_INTERFACE"),
    ("REALITY_TEST_INTERFACE", "TESTS_AGAINST", "REALITY"),
    ("RVTP", "UPDATES", "GIA_TAI"),
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


def edge_set_from(graph, node_ids):
    relation_types = set(graph.get("relation_types", []))
    edge_set = set()
    for edge in graph.get("edges", []):
        src, typ, dst = edge.get("from"), edge.get("type"), edge.get("to")
        if typ not in relation_types:
            fail(f"edge uses undeclared relation type: {src} -[{typ}]-> {dst}")
        if src not in node_ids and src != "BL-INF-UNIFY":
            fail(f"edge source does not exist: {src}")
        if dst not in node_ids and dst != "BL-INF-UNIFY":
            fail(f"edge target does not exist: {dst}")
        edge_set.add((src, typ, dst))
    return edge_set


def main() -> None:
    graph = load_json(GRAPH_PATH)
    topology = load_json(TOPOLOGY_PATH)
    constituents = load_json(CONSTITUENTS_PATH)
    logic_stack = load_json(LOGIC_STACK_PATH)

    for doc in CANONICAL_DOCS:
        if not doc.exists():
            fail(f"missing canonical unification document: {doc.relative_to(ROOT)}")

    if graph.get("id") != "BL-INF-UNIFY":
        fail("graph id must be BL-INF-UNIFY")
    if graph.get("actuality_authority") != "REALITY":
        fail("actuality_authority must be REALITY")
    if graph.get("generative_precedence") != "MODE_DEPENDENT":
        fail("generative_precedence must be MODE_DEPENDENT")
    if graph.get("public_projection") is not True:
        fail("unified graph must declare public_projection=true")
    if graph.get("not_runtime_router") is not True:
        fail("unified graph must declare not_runtime_router=true")
    if graph.get("not_identity_collapse") is not True:
        fail("unified graph must declare not_identity_collapse=true")
    if graph.get("not_fixed_hierarchy") is not True:
        fail("unified graph must reject a fixed Reality/BL∞/GiaTai hierarchy")
    if graph.get("no_absolute_epistemic_parent") is not True:
        fail("unified graph must declare no_absolute_epistemic_parent=true")

    node_ids = {n.get("id") for n in graph.get("nodes", [])}
    missing_nodes = REQUIRED_NODES - node_ids
    if missing_nodes:
        fail(f"missing required nodes: {sorted(missing_nodes)}")

    edge_set = edge_set_from(graph, node_ids)
    missing_edges = REQUIRED_EDGES - edge_set
    if missing_edges:
        fail(f"missing required integration edges: {sorted(missing_edges)}")

    for node in RVP_GOVERNED:
        if ("RVP", "GOVERNS", node) not in edge_set:
            fail(f"Reality Veto governance edge missing for {node}")

    if ("OHAS", "GOVERNS", "REALITY") in edge_set or ("OHAS", "CONSTRAINS", "REALITY") in edge_set:
        fail("OHAS must never be modeled as governing/constraining REALITY")

    # A fixed canonical cycle starting only from Reality is no longer allowed as the current topology.
    if "canonical_cycle" in graph:
        fail("fixed canonical_cycle is obsolete; use THUC_DINH/GIA_DINH mode_cycles")

    modes = graph.get("mode_cycles", {})
    thuc = modes.get("THUC_DINH", [])
    gia = modes.get("GIA_DINH", [])
    if not thuc or thuc[0] != "REALITY" or "BL∞" not in thuc or "GIA_TAI" not in thuc:
        fail("THUC_DINH cycle must be Reality-led and include BL∞ and GIA_TAI")
    if not gia or gia[0] != "GIA_TAI" or "BL∞" not in gia or "REALITY" not in gia:
        fail("GIA_DINH cycle must be GiaTai-led and return through BL∞ to REALITY")

    # Dedicated topology contract must encode the same dual-mode logic.
    if topology.get("id") != "BL-RG-TOPOLOGY":
        fail("dynamic topology id must be BL-RG-TOPOLOGY")
    if topology.get("not_fixed_hierarchy") is not True:
        fail("dynamic topology must reject fixed hierarchy")
    axes = topology.get("authority_axes", {})
    if axes.get("actuality_authority") != "REALITY":
        fail("topology actuality authority must be REALITY")
    if axes.get("generative_precedence") != "MODE_DEPENDENT":
        fail("topology generative precedence must be MODE_DEPENDENT")
    topo_modes = topology.get("modes", {})
    if topo_modes.get("THUC_DINH", {}).get("generative_sequence", [None])[0] != "REALITY":
        fail("topology THUC_DINH must start from REALITY")
    if topo_modes.get("GIA_DINH", {}).get("generative_sequence", [None])[0] != "GIA_TAI":
        fail("topology GIA_DINH must start from GIA_TAI")

    if logic_stack.get("not_fixed_hierarchy") is not True:
        fail("machine logic stack must declare not_fixed_hierarchy=true")
    if "47_CANONICAL_DYNAMIC_REALITY_GIA_TAI_STACK.md" not in logic_stack.get("canonical_dynamic_source", ""):
        fail("machine logic stack must point to dynamic canonical source")
    if "THUC_DINH" not in logic_stack.get("mode_cycles", {}) or "GIA_DINH" not in logic_stack.get("mode_cycles", {}):
        fail("machine logic stack must expose both THUC_DINH and GIA_DINH")

    progress = graph.get("progress_condition", "").lower()
    if "delta" not in progress:
        fail("progress_condition must require an inspectable delta")

    profile_ids = {p.get("id") for p in constituents.get("profiles", [])}
    missing_profiles = REQUIRED_PROFILE_IDS - profile_ids
    if missing_profiles:
        fail(f"missing required constituent profiles: {sorted(missing_profiles)}")

    public_keys = (
        set(walk_keys(graph))
        | set(walk_keys(topology))
        | set(walk_keys(constituents))
        | set(walk_keys(logic_stack))
    )
    leaked_keys = FORBIDDEN_PUBLIC_KEYS & public_keys
    if leaked_keys:
        fail(f"protected runtime concepts exposed as machine object keys: {sorted(leaked_keys)}")

    print("[BL-INF-UNIFY AUDIT] PASS")
    print(f"nodes={len(node_ids)} edges={len(graph.get('edges', []))} profiles={len(profile_ids)}")
    print("Dynamic Reality-GiaTai precedence, Reality actuality authority, identity preservation and dual recursive modes passed.")


if __name__ == "__main__":
    main()
