from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Enforce BL-CPR public release boundary")
parser.add_argument("--strict", action="store_true")
args = parser.parse_args()

errors = []
notes = []

required = [
    ROOT / "DISCLOSURE_POLICY.md",
    ROOT / "machine/disclosure-policy.json",
    ROOT / "BL-ADN.md",
    ROOT / "provenance/00_PUBLIC_PROVENANCE.md",
]
for path in required:
    if not path.exists():
        errors.append(f"missing required public protocol file: {path.relative_to(ROOT)}")

try:
    policy = json.loads((ROOT / "machine/disclosure-policy.json").read_text(encoding="utf-8"))
except Exception as exc:
    policy = {}
    errors.append(f"invalid disclosure policy JSON: {exc}")

for field in [
    "policy_id", "version", "status", "decision", "public_required",
    "controlled_or_protected", "forbidden_path_prefixes", "forbidden_filename_tokens",
    "public_machine_contract",
]:
    if not policy.get(field):
        errors.append(f"disclosure policy missing field: {field}")
if policy.get("policy_id") != "BL-CPR":
    errors.append("unexpected disclosure policy id")

try:
    bl_adn = (ROOT / "BL-ADN.md").read_text(encoding="utf-8")
except Exception as exc:
    bl_adn = ""
    errors.append(f"invalid BL-ADN source: {exc}")
for marker in ["# XXV. CỔNG CÔNG KHAI BL-CPR", 'version: "0.2.0"']:
    if marker not in bl_adn:
        errors.append(f"BL-ADN source missing marker: {marker}")


def tracked_files():
    try:
        output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT, stderr=subprocess.DEVNULL)
        return [ROOT / p.decode("utf-8") for p in output.split(b"\0") if p]
    except Exception:
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


files = tracked_files()
forbidden_prefixes = [str(x).replace("\\", "/").lower() for x in policy.get("forbidden_path_prefixes", [])]
forbidden_filename_tokens = [str(x).lower() for x in policy.get("forbidden_filename_tokens", [])]
for path in files:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    rel_lower = rel_posix.lower()
    name_lower = rel.name.lower()
    for prefix in forbidden_prefixes:
        if rel_lower == prefix.rstrip("/") or rel_lower.startswith(prefix):
            errors.append(f"forbidden public path: {rel_posix}")
            break
    for token in forbidden_filename_tokens:
        if token in name_lower:
            errors.append(f"protected runtime filename in public release: {rel_posix}")
            break
    if rel.name.lower().startswith(".env") and rel.name != ".env.example":
        errors.append(f"environment file in public release: {rel_posix}")
    if rel.suffix.lower() in {".key", ".pem", ".p12", ".pfx", ".keystore"}:
        errors.append(f"key/certificate material in public release: {rel_posix}")

reference_scan_exclusions = {
    Path("DISCLOSURE_POLICY.md"), Path("machine/disclosure-policy.json"),
    Path("scripts/disclosure_audit.py"), Path("content/39_PUBLIC_DISCLOSURE_AND_RUNTIME_BOUNDARY.md"),
    Path(".gitignore"),
}
protected_reference_patterns = [
    re.compile(r"handoff/BL_INFINITY_HANDOFF", re.I),
    re.compile(r"NEXT_MODEL_PROMPT", re.I),
    re.compile(r"provenance/0[0-3]_(?:ORIGIN_TIMELINE|REASONING_LINEAGE|CONVERSATION_LOG_STRUCTURED|RAW_TRANSCRIPT_IMPORT)", re.I),
    re.compile(r"provenance/raw/", re.I),
]
scan_extensions = {".md", ".txt", ".json", ".jsonld", ".yml", ".yaml", ".html", ".js", ".css", ".py"}
for path in files:
    rel = path.relative_to(ROOT)
    if rel in reference_scan_exclusions or path.suffix.lower() not in scan_extensions:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for pattern in protected_reference_patterns:
        if pattern.search(text):
            errors.append(f"public file routes to protected runtime/provenance object: {rel.as_posix()}")
            break

secret_patterns = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}
secret_scan_exclusions = {Path("scripts/disclosure_audit.py"), Path("machine/disclosure-policy.json")}
for path in files:
    rel = path.relative_to(ROOT)
    if rel in secret_scan_exclusions or path.suffix.lower() not in scan_extensions:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for label, pattern in secret_patterns.items():
        if pattern.search(text):
            errors.append(f"possible {label} in {rel.as_posix()}")

build_path = ROOT / "scripts/build.py"
if not build_path.exists():
    errors.append("missing site build script: scripts/build.py")
else:
    build_source = build_path.read_text(encoding="utf-8")
    for marker in ["PUBLIC_PROVENANCE_FILES", "PUBLIC_CRITIQUE_FILES", "machine/disclosure-policy.json", "bl-adn.html", "bl-adn.md"]:
        if marker not in build_source:
            errors.append(f"site build missing disclosure-safe marker: {marker}")
    unsafe_renderers = [
        "sorted((ROOT/'provenance').glob('*.md'))", 'sorted((ROOT/"provenance").glob("*.md"))',
        "sorted((ROOT/'critiques').glob('*.md'))", 'sorted((ROOT/"critiques").glob("*.md"))',
    ]
    for marker in unsafe_renderers:
        if marker in build_source:
            errors.append("site build still auto-publishes directory contents instead of an allowlist")
            break

reverse_path = ROOT / "machine/bl-reverse-system.json"
if reverse_path.exists():
    try:
        reverse = json.loads(reverse_path.read_text(encoding="utf-8"))
        for protected_key in ["pipeline", "automatic_triggers", "attack_operators", "default_targets", "routing_weights", "private_diagnostics"]:
            if protected_key in reverse:
                errors.append(f"BL-REV public contract contains protected production field: {protected_key}")
        if reverse.get("contract_scope") != "PUBLIC_INTERFACE_ONLY":
            errors.append("BL-REV public contract missing PUBLIC_INTERFACE_ONLY scope")
    except Exception as exc:
        errors.append(f"invalid BL-REV public contract: {exc}")

# Public logic stack may be static, dynamic, or open-ended dynamic conceptual view; never a runtime router.
logic_stack_path = ROOT / "machine/logic-stack.json"
if not logic_stack_path.exists():
    errors.append("missing public logic stack")
else:
    try:
        logic_stack = json.loads(logic_stack_path.read_text(encoding="utf-8"))
        graph_type = logic_stack.get("graph_type")
        allowed_graph_types = {"LOGICAL_GRAPH_VIEW", "DYNAMIC_LOGICAL_GRAPH_VIEW", "DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW"}
        if graph_type not in allowed_graph_types:
            errors.append("logic stack must remain an approved public conceptual logical view")
        if logic_stack.get("interface_scope") != "PUBLIC_CONCEPTUAL_DEPENDENCY_VIEW_ONLY":
            errors.append("logic stack missing public conceptual-only scope")
        if logic_stack.get("not_runtime_router") is not True:
            errors.append("logic stack must explicitly declare not_runtime_router=true")
        if graph_type in {"DYNAMIC_LOGICAL_GRAPH_VIEW", "DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW"}:
            if logic_stack.get("not_fixed_hierarchy") is not True:
                errors.append("dynamic logic stack must explicitly reject fixed hierarchy")
            modes = logic_stack.get("mode_cycles", {})
            if "THUC_DINH" not in modes or "GIA_DINH" not in modes:
                errors.append("dynamic public logic stack must expose both THUC_DINH and GIA_DINH")
        if graph_type == "DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW":
            if logic_stack.get("not_exhaustive_taxonomy") is not True:
                errors.append("open-ended public logic stack must reject exhaustive taxonomy")
            modes = logic_stack.get("mode_cycles", {})
            if "UNKNOWN_DISCOVERY" not in modes or "MIXED_CONTESTED" not in modes:
                errors.append("open-ended public logic stack must expose Unknown and mixed/contested routes")
            if logic_stack.get("open_ended_phase_space") != "open-ended-epistemic-phase-space.json":
                errors.append("open-ended public logic stack missing phase-space pointer")
        for protected_key in ["router", "routing_weights", "activation_triggers", "operator_sequence", "production_pipeline", "private_diagnostics", "target_ranking"]:
            if protected_key in logic_stack:
                errors.append(f"public logic stack contains protected runtime field: {protected_key}")
    except Exception as exc:
        errors.append(f"invalid public logic stack: {exc}")

# Dedicated dynamic topology is a public conceptual contract only.
topology_path = ROOT / "machine/reality-gia-tai-topology.json"
if topology_path.exists():
    try:
        topology = json.loads(topology_path.read_text(encoding="utf-8"))
        if topology.get("id") != "BL-RG-TOPOLOGY":
            errors.append("unexpected Reality-GiaTai topology id")
        if topology.get("not_fixed_hierarchy") is not True:
            errors.append("Reality-GiaTai topology must reject fixed hierarchy")
        if topology.get("not_runtime_router") is not True:
            errors.append("Reality-GiaTai topology must declare not_runtime_router=true")
        axes = topology.get("authority_axes", {})
        if axes.get("actuality_authority") != "REALITY" or axes.get("generative_precedence") != "MODE_DEPENDENT":
            errors.append("Reality-GiaTai topology must separate REALITY actuality authority from MODE_DEPENDENT generative precedence")
        for protected_key in ["router", "routing_weights", "activation_triggers", "operator_sequence", "production_pipeline", "private_diagnostics", "target_ranking"]:
            if protected_key in topology:
                errors.append(f"Reality-GiaTai public topology contains protected runtime field: {protected_key}")
    except Exception as exc:
        errors.append(f"invalid Reality-GiaTai public topology: {exc}")

# Open-ended phase space may expose only conceptual dimensions, named regions and public engine contracts.
phase_path = ROOT / "machine/open-ended-epistemic-phase-space.json"
if not phase_path.exists():
    errors.append("missing public open-ended epistemic phase-space contract")
else:
    try:
        phase = json.loads(phase_path.read_text(encoding="utf-8"))
        if phase.get("id") != "BL-OEPS":
            errors.append("unexpected open-ended phase-space id")
        if phase.get("public_projection") is not True or phase.get("not_runtime_router") is not True:
            errors.append("open-ended phase space must remain public conceptual projection only")
        if phase.get("taxonomy_is_exhaustive") is not False or phase.get("dimensions_are_extensible") is not True:
            errors.append("open-ended phase space must remain non-exhaustive and dimension-extensible")
        for protected_key in ["router", "routing_weights", "activation_triggers", "operator_sequence", "production_pipeline", "private_diagnostics", "target_ranking"]:
            if protected_key in phase:
                errors.append(f"open-ended public phase space contains protected runtime field: {protected_key}")
    except Exception as exc:
        errors.append(f"invalid open-ended public phase space: {exc}")

reverse_doctrine_path = ROOT / "content/40_BL_REVERSE_SOVEREIGN_ADVERSARY.md"
if not reverse_doctrine_path.exists():
    errors.append("missing public BL-REV doctrine")
else:
    reverse_doctrine = reverse_doctrine_path.read_text(encoding="utf-8")
    reverse_doctrine_lower = reverse_doctrine.lower()
    for marker in ["public_doctrine_only", "public verification contract", "protected runtime boundary"]:
        if marker not in reverse_doctrine_lower:
            errors.append(f"BL-REV public doctrine missing disclosure marker: {marker}")
    forbidden_doctrine_runtime = [
        "## 5. các toán tử bl-rev", "## 6. quy trình đối kháng chuẩn", "## 9. trigger tự động",
        "## 10. sản phẩm đầu ra bắt buộc", "`prior_inversion`", "`objective_negation`",
        "`boundary_as_asset`", "`voluntary_binding`", "`stopping_operator`", "automatic_triggers",
        "attack_operators", "production sequencing", "target ranking",
    ]
    boundary_index = reverse_doctrine_lower.find("## 10. protected runtime boundary")
    for marker in forbidden_doctrine_runtime:
        found_at = reverse_doctrine_lower.find(marker)
        if found_at == -1:
            continue
        if marker in {"production sequencing", "target ranking"} and boundary_index != -1 and found_at > boundary_index:
            continue
        errors.append(f"BL-REV public doctrine exposes protected runtime semantic: {marker}")

marker_files = {
    ROOT / "content/32_REASONING_TO_CLAIM_MAP.md": "PUBLIC_DERIVATION_MAP",
    ROOT / "critiques/03_WEEKLY_REFINEMENT_PROTOCOL.md": "PUBLIC_INTERFACE_ONLY",
    ROOT / "content/40_BL_REVERSE_SOVEREIGN_ADVERSARY.md": "PUBLIC_DOCTRINE_ONLY",
}
for path, marker in marker_files.items():
    if not path.exists():
        errors.append(f"missing disclosure-safe public file: {path.relative_to(ROOT)}")
        continue
    text = path.read_text(encoding="utf-8")
    if marker not in text:
        errors.append(f"{path.relative_to(ROOT)} missing disclosure scope marker: {marker}")

notes.append(f"checked {len(files)} tracked/public files")
result = {"policy": policy.get("policy_id"), "policy_version": policy.get("version"), "errors": sorted(set(errors)), "notes": notes}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors and args.strict:
    sys.exit(1)
