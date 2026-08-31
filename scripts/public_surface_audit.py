#!/usr/bin/env python3
"""Fail closed if the repository stops being a minimal public projection."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    ".github/workflows/pages.yml",
    ".gitignore",
    "CITATION.cff",
    "CONTROLLED_ACCESS.md",
    "DISCLOSURE_POLICY.md",
    "LICENSE-CODE",
    "LICENSE-CONTENT",
    "README.md",
    "SECURITY.md",
    "index.html",
    "machine/public-capability-contract.json",
    "robots.txt",
    "scripts/public_surface_audit.py",
    "sitemap.xml",
}
BLOCKED_PATH_PARTS = {"experiment", "prototype", "runtime", "internal", "private", "kernel", "console"}
BLOCKED_CONTENT = re.compile(
    r"(?i)(private[_ -]?graph|runtime[_ -]?policy|internal[_ -]?(operator|router)|prototype[_ -]?engine)"
)

errors = []
files = {
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob("*")
    if p.is_file() and ".git" not in p.parts
}
for path in sorted(files - ALLOWED):
    errors.append(f"not allowlisted: {path}")
for path in sorted(files):
    lowered = path.lower()
    if any(part in lowered for part in BLOCKED_PATH_PARTS):
        errors.append(f"blocked path class: {path}")
    if path == "scripts/public_surface_audit.py":
        continue
    try:
        text = (ROOT / path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"binary file not allowed: {path}")
        continue
    if BLOCKED_CONTENT.search(text):
        errors.append(f"blocked implementation marker: {path}")

if errors:
    print("PUBLIC SURFACE AUDIT FAILED", file=sys.stderr)
    print("\n".join(f"- {item}" for item in errors), file=sys.stderr)
    raise SystemExit(1)
print(f"PUBLIC SURFACE AUDIT OK: {len(files)} allowlisted files")
