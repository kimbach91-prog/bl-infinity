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
required = [ROOT / "DISCLOSURE_POLICY.md", ROOT / "machine/disclosure-policy.json"]
for path in required:
    if not path.exists():
        errors.append(f"missing required BL-CPR file: {path.relative_to(ROOT)}")

try:
    policy = json.loads((ROOT / "machine/disclosure-policy.json").read_text(encoding="utf-8"))
except Exception as exc:
    policy = {}
    errors.append(f"invalid disclosure policy JSON: {exc}")

for field in ["policy_id", "version", "status", "decision", "public_required", "forbidden_in_public_release"]:
    if not policy.get(field):
        errors.append(f"disclosure policy missing field: {field}")
if policy.get("policy_id") != "BL-CPR":
    errors.append("unexpected disclosure policy id")

def tracked_files():
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return [ROOT / p.decode("utf-8") for p in output.split(b"\0") if p]
    except Exception:
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]

files = tracked_files()
forbidden_names = {str(x).lower() for x in policy.get("forbidden_in_public_release", [])}

for path in files:
    rel = path.relative_to(ROOT)
    lowered_parts = {part.lower() for part in rel.parts}
    if forbidden_names & lowered_parts:
        errors.append(f"forbidden public path: {rel}")
    if rel.name.lower().startswith(".env") and rel.name != ".env.example":
        errors.append(f"environment file in public release: {rel}")
    if rel.suffix.lower() in {".key", ".pem", ".p12", ".pfx", ".keystore"}:
        errors.append(f"key/certificate material in public release: {rel}")


build_path = ROOT / "scripts/build.py"
if not build_path.exists():
    errors.append("missing site build script: scripts/build.py")
else:
    build_source = build_path.read_text(encoding="utf-8")
    for marker in ["'disclosure_policy':'disclosure-policy.json'", "machine/disclosure-policy.json"]:
        if marker not in build_source:
            errors.append(f"site build does not publish BL-CPR marker: {marker}")

secret_patterns = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}

scan_extensions = {".md", ".txt", ".json", ".jsonld", ".yml", ".yaml", ".html", ".js", ".css"}
excluded = {Path("scripts/disclosure_audit.py"), Path("machine/disclosure-policy.json")}
for path in files:
    rel = path.relative_to(ROOT)
    if rel in excluded or path.suffix.lower() not in scan_extensions:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for label, pattern in secret_patterns.items():
        if pattern.search(text):
            errors.append(f"possible {label} in {rel}")

notes.append(f"checked {len(files)} tracked/public files")
result = {
    "policy": policy.get("policy_id"),
    "policy_version": policy.get("version"),
    "errors": sorted(set(errors)),
    "notes": notes,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors and args.strict:
    sys.exit(1)

