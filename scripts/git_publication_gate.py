from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "machine" / "git-write-gate.json"
DISCLOSURE_PATH = ROOT / "machine" / "disclosure-policy.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "pages.yml"

parser = argparse.ArgumentParser(description="BL-GWG fail-closed public Git write gate")
parser.add_argument("--strict", action="store_true")
parser.add_argument("--tree", action="store_true", help="scan all tracked files")
args = parser.parse_args()

errors = []
notes = []


def fail(msg):
    errors.append(msg)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot load {path.relative_to(ROOT)}: {exc}")
        return {}


policy = load_json(POLICY_PATH)
disclosure = load_json(DISCLOSURE_PATH)

if policy.get("policy_id") != "BL-GWG":
    fail("missing BL-GWG policy identity")
if policy.get("default_decision") != "DENY_UNTIL_ALL_GATES_PASS":
    fail("BL-GWG must remain fail-closed")
if policy.get("publication_requires_explicit_owner_command") is not True:
    fail("public publication must require explicit owner command")
if policy.get("owner_publication_freeze") is not True:
    fail("owner publication freeze must remain active")
if policy.get("pre_write_required") is not True or policy.get("post_write_audit_required") is not True:
    fail("BL-GWG requires both pre-write and post-write gates")

required_invariants = {
    "PUBLIC_GIT_WRITE_IS_AN_EXPOSURE_EVENT",
    "NO_SINGLE_SECURITY_LAYER_IS_SUFFICIENT",
    "FAIL_CLOSED_ON_UNKNOWN_DISCLOSURE_CLASS",
    "PROTECTED_RUNTIME_NEVER_BECOMES_PUBLIC_BY_CONVENIENCE",
    "AUTOMATION_MAY_AUDIT_BUT_MAY_NOT_AUTO_PUBLISH",
}
if not required_invariants.issubset(set(policy.get("invariants", []))):
    fail("BL-GWG missing required invariants")

try:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]
except Exception as exc:
    fail(f"cannot enumerate tracked files: {exc}")
    files = []

forbidden_prefixes = [str(x).replace("\\", "/").lower() for x in disclosure.get("forbidden_path_prefixes", [])]
forbidden_tokens = [str(x).lower() for x in disclosure.get("forbidden_filename_tokens", [])]

secret_patterns = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Stripe live secret": re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b"),
}

scan_ext = {".md", ".txt", ".json", ".jsonld", ".yml", ".yaml", ".html", ".js", ".css", ".py"}
secret_reference_exclusions = {
    Path("scripts/git_publication_gate.py"),
    Path("scripts/security_audit.py"),
    Path("scripts/disclosure_audit.py"),
    Path("SECURITY.md"),
    Path("DISCLOSURE_POLICY.md"),
    Path("machine/disclosure-policy.json"),
    Path("machine/git-write-gate.json"),
}

for path in files:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    rel_lower = rel_posix.lower()
    name_lower = rel.name.lower()

    for prefix in forbidden_prefixes:
        prefix = prefix.rstrip("/")
        if rel_lower == prefix or rel_lower.startswith(prefix + "/"):
            fail(f"forbidden public path: {rel_posix}")
            break

    for token in forbidden_tokens:
        if token in name_lower:
            fail(f"protected filename token in public repository: {rel_posix}")
            break

    if rel.name.lower().startswith(".env") and rel.name != ".env.example":
        fail(f"environment file in public repository: {rel_posix}")
    if rel.suffix.lower() in {".key", ".pem", ".p12", ".pfx", ".keystore"}:
        fail(f"key or certificate material in public repository: {rel_posix}")

    if rel.suffix.lower() not in scan_ext:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue

    if rel not in secret_reference_exclusions:
        for label, pattern in secret_patterns.items():
            if pattern.search(text):
                fail(f"possible {label} in public file: {rel_posix}")

    if re.search(r"javascript\s*:", text, flags=re.I):
        if rel not in {Path("scripts/security_audit.py"), Path("scripts/git_publication_gate.py"), Path("SECURITY.md")}:
            fail(f"unsafe javascript URL pattern in public file: {rel_posix}")
    if re.search(r"data\s*:\s*text/html", text, flags=re.I):
        if rel not in {Path("scripts/security_audit.py"), Path("scripts/git_publication_gate.py"), Path("SECURITY.md")}:
            fail(f"unsafe data:text/html pattern in public file: {rel_posix}")

workflow = WORKFLOW_PATH.read_text(encoding="utf-8") if WORKFLOW_PATH.exists() else ""
for marker in [
    "automated events are AUDIT-ONLY",
    "github.event_name == 'workflow_dispatch'",
    "Upload Pages artifact only on explicit manual publish",
    "Notify IndexNow only after explicit manual publish",
]:
    if marker not in workflow:
        fail(f"publication freeze workflow marker missing: {marker}")
if "pull_request_target" in workflow:
    fail("pull_request_target is forbidden")

# Hard server-side pre-receive enforcement cannot be provided by repository files alone.
# Keep this visible so code-level checks are never misrepresented as branch protection.
if policy.get("server_side_ruleset_required_for_hard_pre_receive_enforcement") is not True:
    fail("BL-GWG must disclose platform ruleset requirement")

notes.append(f"scanned {len(files)} tracked files")
notes.append("BL-GWG code gate verifies repository state; hard pre-receive blocking still requires GitHub ruleset/branch protection")
result = {"policy": "BL-GWG", "errors": sorted(set(errors)), "notes": notes}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors and args.strict:
    sys.exit(1)
