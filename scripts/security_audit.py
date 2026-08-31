from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

parser = argparse.ArgumentParser(description="BL∞ public security and bilingual-integrity audit")
parser.add_argument("--strict", action="store_true")
parser.add_argument("--site", action="store_true", help="also audit generated site output")
args = parser.parse_args()

errors = []
warnings = []
notes = []

required = [
    ROOT / "SECURITY.md",
    ROOT / "DISCLOSURE_POLICY.md",
    ROOT / "machine/security-profile.json",
    ROOT / "translations/translation-index.json",
    ROOT / "translations/en/README.md",
    ROOT / "translations/en/THEORY_CORE.md",
    ROOT / "public/academic-democracy-technology.html",
    ROOT / "scripts/build.py",
    ROOT / "scripts/harden_site.py",
    ROOT / ".github/workflows/pages.yml",
]
for path in required:
    if not path.exists():
        errors.append(f"missing required security/bilingual file: {path.relative_to(ROOT)}")

# Translation provenance must stay explicit about partial coverage.
try:
    tindex = json.loads((ROOT / "translations/translation-index.json").read_text(encoding="utf-8"))
except Exception as exc:
    tindex = {}
    errors.append(f"invalid translation index: {exc}")

if tindex.get("policy") != "TRANSLATION_IS_DERIVATIVE_REPRESENTATION_NOT_INDEPENDENT_THEORY_VERSION":
    errors.append("translation index missing derivative-representation policy")
en = tindex.get("languages", {}).get("en", {})
for key in ["role", "entry", "coverage", "source_files", "translation_files", "review_status", "known_gap"]:
    if not en.get(key):
        errors.append(f"English translation index missing {key}")
if en.get("coverage") == "FULL" and en.get("review_status") != "HUMAN_REVIEWED_FULL":
    errors.append("English translation cannot claim FULL without HUMAN_REVIEWED_FULL")
for rel in list(en.get("source_files", [])) + list(en.get("translation_files", [])):
    if not (ROOT / rel).exists():
        errors.append(f"translation index points to missing file: {rel}")

# Hardening is deliberately separated from the legacy source renderer: check the hardener itself.
hardener_path = ROOT / "scripts/harden_site.py"
hardener_source = hardener_path.read_text(encoding="utf-8") if hardener_path.exists() else ""
for marker in [
    "escape=True",
    "Content-Security-Policy",
    "strict-origin-when-cross-origin",
    "translation-status.json",
    "security-profile.json",
    "en/theory.html",
    "academic-democracy-technology.html",
    "sha256_file",
    "hreflang",
]:
    if marker not in hardener_source:
        errors.append(f"harden_site.py missing hardening marker: {marker}")

# GitHub Actions: immutable action references, no pull_request_target, no persisted checkout credentials.
workflow_path = ROOT / ".github/workflows/pages.yml"
workflow = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
if "pull_request_target" in workflow:
    errors.append("pages workflow must not use pull_request_target")
uses_lines = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, flags=re.M)
for ref in uses_lines:
    if ref.startswith("./"):
        continue
    if "@" not in ref:
        errors.append(f"GitHub Action missing immutable ref: {ref}")
        continue
    version = ref.rsplit("@", 1)[1]
    if not re.fullmatch(r"[0-9a-f]{40}", version):
        errors.append(f"GitHub Action not pinned to full commit SHA: {ref}")
for marker in [
    "persist-credentials: false",
    "python scripts/security_audit.py --strict",
    "python scripts/harden_site.py",
    "python scripts/security_audit.py --strict --site",
    "pip-audit -r requirements.txt",
    "cp public/academic-democracy-technology.html site/academic-democracy-technology.html",
]:
    if marker not in workflow:
        errors.append(f"pages workflow missing security marker: {marker}")
if "permissions:" not in workflow:
    errors.append("workflow must declare explicit permissions")

# Direct Python build dependencies are exact pinned; security tooling is independently pinned.
def exact_requirements(path: Path):
    if not path.exists():
        errors.append(f"missing dependency lock input: {path.name}")
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "git+" in line or "http://" in line or "https://" in line:
            errors.append(f"direct URL/VCS dependency forbidden in {path.name}: {line}")
        if "==" not in line:
            errors.append(f"dependency must be exact-version pinned in {path.name}: {line}")


exact_requirements(ROOT / "requirements.txt")
exact_requirements(ROOT / "requirements-security.txt")

# Source-level obvious unsafe URL schemes and common high-confidence secret formats.
scan_ext = {".md", ".txt", ".json", ".jsonld", ".yml", ".yaml", ".html", ".js", ".css", ".py"}
source_exclusions = {
    Path("scripts/security_audit.py"),
    Path("scripts/disclosure_audit.py"),
    Path("SECURITY.md"),
    Path("DISCLOSURE_POLICY.md"),
    Path("machine/disclosure-policy.json"),
}
# These documents describe blocked URL schemes literally. They remain inside the secret scan;
# only the URL-execution heuristic is suppressed to avoid security-documentation false positives.
url_scan_exclusions = source_exclusions | {
    Path("content/26_SECURITY_AND_INTEGRITY_MODEL.md"),
    Path("machine/security-profile.json"),
}
secret_patterns = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Stripe live secret": re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b"),
}
for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "site" in path.parts or path.suffix.lower() not in scan_ext:
        continue
    rel = path.relative_to(ROOT)
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if rel not in url_scan_exclusions:
        if re.search(r"javascript\s*:", text, flags=re.I):
            errors.append(f"unsafe javascript: URL in public source: {rel.as_posix()}")
        if re.search(r"data\s*:\s*text/html", text, flags=re.I):
            errors.append(f"unsafe data:text/html URL in public source: {rel.as_posix()}")
    if rel not in source_exclusions:
        for label, pattern in secret_patterns.items():
            if pattern.search(text):
                errors.append(f"possible {label} in {rel.as_posix()}")

# Generated site audit is the final active-content boundary after all render/discovery steps.
if args.site:
    if not SITE.exists():
        errors.append("--site requested but generated site/ does not exist")
    else:
        html_files = list(SITE.rglob("*.html"))
        if not html_files:
            errors.append("generated site contains no HTML")
        for path in html_files:
            rel = path.relative_to(SITE)
            text = path.read_text(encoding="utf-8")
            if 'http-equiv="Content-Security-Policy"' not in text:
                errors.append(f"generated HTML missing CSP: {rel.as_posix()}")
            if 'name="referrer" content="strict-origin-when-cross-origin"' not in text:
                errors.append(f"generated HTML missing strict referrer policy: {rel.as_posix()}")
            if re.search(r"\son[a-z]+\s*=", text, flags=re.I):
                errors.append(f"inline event handler found in generated HTML: {rel.as_posix()}")
            if re.search(r"\sstyle\s*=", text, flags=re.I):
                errors.append(f"inline style attribute found in generated HTML: {rel.as_posix()}")
            if re.search(r"<(?:script|img|iframe|link)\b[^>]*(?:src|href)=['\"]http://", text, flags=re.I):
                errors.append(f"insecure active-resource URL in generated HTML: {rel.as_posix()}")
            for attrs in re.findall(r"<script\b([^>]*)>", text, flags=re.I):
                src = re.search(r"\bsrc=['\"]([^'\"]+)", attrs, flags=re.I)
                if src:
                    value = src.group(1)
                    if not (
                        value.startswith("assets/")
                        or value.startswith("../")
                        or value.startswith("../../")
                        or value.startswith("https://giscus.app/")
                    ):
                        errors.append(f"unexpected external script source in {rel.as_posix()}: {value}")
                elif "application/ld+json" not in attrs:
                    errors.append(f"unexpected inline executable script in generated HTML: {rel.as_posix()}")
        for rel in [
            "machine/security-profile.json",
            "machine/translation-status.json",
            "en/theory.html",
            "en/index.html",
            "translations/translation-index.json",
            "academic-democracy-technology.html",
        ]:
            if not (SITE / rel).exists():
                errors.append(f"generated bilingual/security artifact missing: {rel}")
        manifest_path = SITE / "machine/manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for field in ["languages", "translation_status", "security_profile", "academic_democracy_technology_profile"]:
                    if not manifest.get(field):
                        errors.append(f"generated machine manifest missing field: {field}")
            except Exception as exc:
                errors.append(f"invalid generated machine manifest: {exc}")
        else:
            errors.append("generated machine manifest missing")
        notes.append(f"audited {len(html_files)} generated HTML files")

result = {
    "errors": sorted(set(errors)),
    "warnings": sorted(set(warnings)),
    "notes": notes,
    "mode": "source+site" if args.site else "source",
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors and args.strict:
    sys.exit(1)
