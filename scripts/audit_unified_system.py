from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "machine" / "bl-infinity-unified-system.json"
TOPOLOGY_PATH = ROOT / "machine" / "reality-gia-tai-topology.json"
PHASE_PATH = ROOT / "machine" / "open-ended-epistemic-phase-space.json"
CONSTITUENTS_PATH = ROOT / "machine" / "unified-constituents.json"
LOGIC_STACK_PATH = ROOT / "machine" / "logic-stack.json"
CANONICAL_DOCS = [
    ROOT / "content" / "43_BL_INFINITY_GRAND_UNIFICATION.md",
    ROOT / "content" / "44_CANONICAL_UNIFIED_LOGIC_STACK.md",
    ROOT / "content" / "45_UNIFIED_CONSTITUENT_PROFILES.md",
    ROOT / "content" / "46_REALITY_GIA_TAI_DUAL_PROPOSITIONS.md",
    ROOT / "content" / "47_CANONICAL_DYNAMIC_REALITY_GIA_TAI_STACK.md",
    ROOT / "content" / "48_OPEN_ENDED_EPISTEMIC_PHASE_SPACE.md",
    ROOT / "content" / "49_CANONICAL_OPEN_ENDED_DISCOVERY_CHAIN.md",
]

REQUIRED_NODES = {
    "REALITY", "GIA_TAI", "UNKNOWN", "OPAQUE_UNKNOWN", "MIXED_ENTANGLEMENT",
    "ANOMALY_RESIDUAL", "BL-RP", "BL-GTP", "BL-OEPS", "BL-UUH", "BL-DGE",
    "BL-OME", "BL-CDE", "REALITY_TEST_INTERFACE", "ACTION_OR_TEST", "BL∞",
    "RVT", "RVP", "RVTP", "RVL", "BLEE", "Academic-Democracy", "BL-HRD",
    "BL-ADN", "BL-LOG", "BL-CHRONO", "BL-PCRO", "BL-OODP", "BLOK",
    "BL-NOVO", "BL-REV", "BL-AEGIS", "BL-SFRET", "OPT-HKRP",
    "OHAS", "KAT", "BL-PIRAL", "SRS", "BL-CPR",
}

REQUIRED_PROFILE_IDS = {
    "BL-RP", "BL-GTP", "BL-OEPS", "BL-UUH", "BL-DGE", "BL-OME", "BL-CDE",
    "RVT", "BLEE", "Academic-Democracy", "KAT", "OPT-HKRP", "OHAS",
    "BL-SFRET", "BL-REV",
}

REQUIRED_EDGES = {
    ("BL-RP", "FORMALIZES", "REALITY"),
    ("BL-GTP", "FORMALIZES", "GIA_TAI"),
    ("REALITY", "LOCATES_IN", "BL-OEPS"),
    ("GIA_TAI", "LOCATES_IN", "BL-OEPS"),
    ("UNKNOWN", "LOCATES_IN", "BL-OEPS"),
    ("OPAQUE_UNKNOWN", "LOCATES_IN", "BL-OEPS"),
    ("MIXED_ENTANGLEMENT", "LOCATES_IN", "BL-OEPS"),
    ("ANOMALY_RESIDUAL", "FEEDS", "BL-UUH"),
    ("UNKNOWN", "FEEDS", "BL-UUH"),
    ("BL-UUH", "ROUTES_TO", "BL-DGE"),
    ("BL-DGE", "PROPOSES_DIMENSION_TO", "BL-OEPS"),
    ("BL-DGE", "ROUTES_TO", "BL-OME"),
    ("BL-OME", "MUTATES_ONTOLOGY_OF", "BL∞"),
    ("BL-OME", "UPDATES", "BL-OEPS"),
    ("BL-OEPS", "ROUTES_TO", "BL-HRD"),
    ("MIXED_ENTANGLEMENT", "ROUTES_TO", "BL-PCRO"),
    ("BL-CDE", "COORDINATES", "BL-OEPS"),
    ("BL-CDE", "COORDINATES", "BL-HRD"),
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
    ("BL-DGE", "ROUTES_TO", "BL-REV"),
    ("BL-OME", "ROUTES_TO", "BL-NOVO"),
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
    "BL∞", "BLEE", "Academic-Democracy", "BL-HRD", "BL-NOVO", "BL-REV",
    "BL-SFRET", "OPT-HKRP", "OHAS", "KAT", "BL-OEPS", "BL-UUH",
    "BL-DGE", "BL-OME", "BL-CDE",
}

REQUIRED_ENGINE_IDS = {"BL-UUH", "BL-DGE", "BL-OME", "BL-CDE"}

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
    phase = load_json(PHASE_PATH)
    constituents = load_json(CONSTITUENTS_PATH)
    logic_stack = load_json(LOGIC_STACK_PATH)

    for doc in CANONICAL_DOCS:
        if not doc.exists():
            fail(f"missing canonical unification document: {doc.relative_to(ROOT)}")

    if graph.get("id") != "BL-INF-UNIFY":
        fail("graph id must be BL-INF-UNIFY")
    if graph.get("actuality_authority") != "REALITY":
        fail("actuality_authority must be REALITY")
    if graph.get("generative_precedence") != "MODE_AND_CONTEXT_DEPENDENT":
        fail("generative_precedence must be MODE_AND_CONTEXT_DEPENDENT")
    if graph.get("taxonomy_status") != "VERSIONED_NON_EXHAUSTIVE":
        fail("taxonomy_status must remain VERSIONED_NON_EXHAUSTIVE")
    if graph.get("public_projection") is not True:
        fail("unified graph must declare public_projection=true")
    if graph.get("not_runtime_router") is not True:
        fail("unified graph must declare not_runtime_router=true")
    if graph.get("not_identity_collapse") is not True:
        fail("unified graph must declare not_identity_collapse=true")
    if graph.get("not_fixed_hierarchy") is not True:
        fail("unified graph must reject a fixed Reality/BL∞/GiaTai hierarchy")
    if graph.get("not_exhaustive_taxonomy") is not True:
        fail("unified graph must reject an exhaustive epistemic taxonomy")
    if graph.get("no_absolute_epistemic_parent") is not True:
        fail("unified graph must declare no_absolute_epistemic_parent=true")
    if "49_CANONICAL_OPEN_ENDED_DISCOVERY_CHAIN.md" not in graph.get("canonical_source", ""):
        fail("unified graph must point to v3 open-ended canonical source")

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

    if "canonical_cycle" in graph:
        fail("fixed canonical_cycle is obsolete; use multiple context-dependent mode cycles")

    modes = graph.get("mode_cycles", {})
    thuc = modes.get("THUC_DINH", [])
    gia = modes.get("GIA_DINH", [])
    unknown = modes.get("UNKNOWN_DISCOVERY", [])
    mixed = modes.get("MIXED_CONTESTED", [])
    if not thuc or thuc[0] != "REALITY" or "BL∞" not in thuc or "GIA_TAI" not in thuc:
        fail("THUC_DINH cycle must be Reality-led and include BL∞ and GIA_TAI")
    if not gia or gia[0] != "GIA_TAI" or "BL∞" not in gia or "REALITY" not in gia:
        fail("GIA_DINH cycle must be GiaTai-led and return through BL∞ to REALITY")
    if not unknown or "BL-UUH" not in unknown or "BL-DGE" not in unknown or "BL-OME" not in unknown:
        fail("UNKNOWN_DISCOVERY route must include UUH, DGE and OME")
    if not mixed or "BL-PCRO" not in mixed or "BL-OEPS" not in mixed:
        fail("MIXED_CONTESTED route must atomize and locate components in the open phase space")

    if topology.get("id") != "BL-RG-TOPOLOGY":
        fail("dynamic topology id must be BL-RG-TOPOLOGY")
    if topology.get("not_fixed_hierarchy") is not True:
        fail("dynamic topology must reject fixed hierarchy")
    axes = topology.get("authority_axes", {})
    if axes.get("actuality_authority") != "REALITY":
        fail("topology actuality authority must be REALITY")
    if axes.get("generative_precedence") != "MODE_DEPENDENT":
        fail("Reality-GiaTai topology generative precedence must remain MODE_DEPENDENT")
    topo_modes = topology.get("modes", {})
    if topo_modes.get("THUC_DINH", {}).get("generative_sequence", [None])[0] != "REALITY":
        fail("topology THUC_DINH must start from REALITY")
    if topo_modes.get("GIA_DINH", {}).get("generative_sequence", [None])[0] != "GIA_TAI":
        fail("topology GIA_DINH must start from GIA_TAI")

    if phase.get("id") != "BL-OEPS":
        fail("open-ended phase-space id must be BL-OEPS")
    if phase.get("taxonomy_is_exhaustive") is not False:
        fail("phase-space taxonomy must explicitly be non-exhaustive")
    if phase.get("dimensions_are_extensible") is not True:
        fail("phase-space dimensions must remain extensible")
    if len(phase.get("current_axes", [])) < 8:
        fail("phase space must expose a meaningful multidimensional public projection")
    unknown_contract = phase.get("unknown_contract", {})
    for marker in [
        "unknown_not_equal_falsehood",
        "opaque_not_equal_meaningless",
        "unknown_unknown_indicator_not_equal_known_content",
        "boundary_awareness_not_equal_outside_content_knowledge",
        "raw_preservation_before_semantic_inflation",
    ]:
        if unknown_contract.get(marker) is not True:
            fail(f"phase-space Unknown invariant missing: {marker}")
    opaque = phase.get("opaque_example", {})
    if opaque.get("raw") != "&;&;@;&;@" or opaque.get("meaning_claimed") is not False:
        fail("opaque example must preserve raw token without claiming meaning")
    engine_ids = {e.get("id") for e in phase.get("engines", [])}
    missing_engines = REQUIRED_ENGINE_IDS - engine_ids
    if missing_engines:
        fail(f"open-ended phase space missing engines: {sorted(missing_engines)}")
    dge_loop = phase.get("dimension_genesis_loop", [])
    if "RETAIN_OR_CONDITIONAL_OR_DORMANT_OR_PRUNE" not in dge_loop or "VERSION_PHASE_SPACE" not in dge_loop:
        fail("dimension genesis must include retention/pruning discipline and versioning")

    if logic_stack.get("graph_type") != "DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW":
        fail("machine logic stack must use DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW")
    if logic_stack.get("not_fixed_hierarchy") is not True:
        fail("machine logic stack must declare not_fixed_hierarchy=true")
    if logic_stack.get("not_exhaustive_taxonomy") is not True:
        fail("machine logic stack must declare not_exhaustive_taxonomy=true")
    if "49_CANONICAL_OPEN_ENDED_DISCOVERY_CHAIN.md" not in logic_stack.get("canonical_open_source", ""):
        fail("machine logic stack must point to v3 open-ended canonical source")
    if logic_stack.get("open_ended_phase_space") != "open-ended-epistemic-phase-space.json":
        fail("machine logic stack missing phase-space machine pointer")
    stack_modes = logic_stack.get("mode_cycles", {})
    for required_mode in ["THUC_DINH", "GIA_DINH", "UNKNOWN_DISCOVERY", "MIXED_CONTESTED"]:
        if required_mode not in stack_modes:
            fail(f"machine logic stack missing mode: {required_mode}")
    entries = set(logic_stack.get("entry_points", []))
    for required_entry in ["REALITY_ANCHORED_OBSERVATION", "GIA_TAI", "OPAQUE_UNKNOWN", "ANOMALY_OR_RESIDUAL"]:
        if required_entry not in entries:
            fail(f"machine logic stack missing entry point: {required_entry}")

    progress = graph.get("progress_condition", "").lower()
    if "delta" not in progress or "dimension" not in progress or "ontology" not in progress:
        fail("progress_condition must include open-ended dimension/ontology deltas")

    profile_ids = {p.get("id") for p in constituents.get("profiles", [])}
    missing_profiles = REQUIRED_PROFILE_IDS - profile_ids
    if missing_profiles:
        fail(f"missing required constituent profiles: {sorted(missing_profiles)}")

    for profile in constituents.get("profiles", []):
        for field in constituents.get("required_fields_for_future_profiles", []):
            if field not in profile:
                fail(f"constituent profile {profile.get('id')} missing required field: {field}")

    public_keys = (
        set(walk_keys(graph))
        | set(walk_keys(topology))
        | set(walk_keys(phase))
        | set(walk_keys(constituents))
        | set(walk_keys(logic_stack))
    )
    leaked_keys = FORBIDDEN_PUBLIC_KEYS & public_keys
    if leaked_keys:
        fail(f"protected runtime concepts exposed as machine object keys: {sorted(leaked_keys)}")

    print("[BL-INF-UNIFY AUDIT] PASS")
    print(
        f"nodes={len(node_ids)} edges={len(graph.get('edges', []))} "
        f"profiles={len(profile_ids)} phase_axes={len(phase.get('current_axes', []))}"
    )
    print(
        "Reality/GiaTai dynamic precedence, Unknown preservation, non-exhaustive phase space, "
        "dimension genesis, ontology mutation and recursive delta checks passed."
    )


if __name__ == "__main__":
    main()
