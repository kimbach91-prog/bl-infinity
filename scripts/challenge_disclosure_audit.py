from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

WITHHELD_LEGACY_FRAGMENTS = {
    "BL-A05-DYNAMIC-REACHABILITY": r"\mathcal R_A(t)=Reach(x_t,U_t)",
    "BL-A06-OBSERVATION-FILTER-COMPOSITION": r"D_A=F_{cognition}\circ F_{detector}\circ F_{access}\circ F_{causal}\circ F_{stability}(\Omega)",
    "BL-A09-PLENITUDE-BRIDGE": r"Cons_L(h)\Rightarrow \exists W\subseteq\Omega:W\models_L h",
    "BL-RCA-RECURSIVE-CAPABILITY-UPDATE": r"U_{n+1}=U_n\cup ConstructibleTools(U_n)",
    "BL-RCA-LONG-HORIZON-REACHABLE-CLOSURE": r"\mathcal R_A^*=\bigcup_{n=0}^{\infty}Reach(x,U_n)",
    "BL-RCA-POSITIVE-ACCESSIBILITY-LIMIT": r"P(\text{never hit }h\text{ in }n\text{ trials})=(1-p_h)^n",
    "OPT-REC-EPISTEMIC-QUALITY": r"Q_{intelligence}\propto ErrorDetectionRate\times RevisionQuality\times UsefulRetention",
    "OPT-REC-VERSION-UPDATE-OPERATOR": r"B_{n+1}=Optimize(B_n,E_n,C_n,T_n)",
}

LOW_DISCOVERY_ROUTES = (
    "challenge.html",
    "research-puzzles.html",
)


def fail(message: str) -> None:
    print(f"CHALLENGE DISCLOSURE AUDIT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def iter_release_text_files():
    roots = [ROOT / "content", ROOT / "public", ROOT / "machine"]
    allowed_suffixes = {".md", ".html", ".txt", ".json", ".jsonld", ".yml", ".yaml"}
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in allowed_suffixes:
                yield path


def audit_withheld_formulas_absent_from_current_tree() -> None:
    texts = []
    for path in iter_release_text_files():
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue

    for object_id, fragment in WITHHELD_LEGACY_FRAGMENTS.items():
        hits = [path.relative_to(ROOT).as_posix() for path, text in texts if fragment in text]
        if hits:
            fail(f"withheld legacy formula {object_id} reappeared in current release tree: {hits}")


def audit_puzzle_source_has_no_answer_key() -> None:
    path = ROOT / "content" / "58_RECONSTRUCTION_PUZZLES.md"
    if not path.exists():
        fail("content/58_RECONSTRUCTION_PUZZLES.md missing")
    text = path.read_text(encoding="utf-8").lower()
    forbidden_headings = ("## đáp án", "## answer key", "## solutions", "## lời giải canonical")
    for heading in forbidden_headings:
        if heading in text:
            fail(f"public puzzle source contains forbidden answer-key heading: {heading}")


def audit_noindex_source_pages() -> None:
    for name in LOW_DISCOVERY_ROUTES:
        path = ROOT / "public" / name
        if not path.exists():
            fail(f"public/{name} missing")
        text = path.read_text(encoding="utf-8").lower()
        for directive in ("noindex", "nofollow", "noarchive", "nosnippet"):
            if directive not in text:
                fail(f"public/{name} missing robots directive {directive}")


def audit_materialized_site() -> None:
    if not SITE.exists():
        fail("site/ missing; run build/staging before --site audit")

    for name in LOW_DISCOVERY_ROUTES:
        path = SITE / name
        if not path.exists():
            fail(f"materialized site missing {name}")
        text = path.read_text(encoding="utf-8").lower()
        for directive in ("noindex", "nofollow", "noarchive", "nosnippet"):
            if directive not in text:
                fail(f"site/{name} lost robots directive {directive}")

    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        text = sitemap.read_text(encoding="utf-8")
        for route in LOW_DISCOVERY_ROUTES:
            if route in text:
                fail(f"low-discovery route leaked into sitemap: {route}")

    llms = SITE / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        for route in LOW_DISCOVERY_ROUTES:
            if route in text:
                fail(f"low-discovery route leaked into llms.txt: {route}")

    manifest = SITE / "machine" / "manifest.json"
    if manifest.exists():
        text = manifest.read_text(encoding="utf-8")
        for route in LOW_DISCOVERY_ROUTES:
            if route in text:
                fail(f"low-discovery route leaked into machine manifest: {route}")


def main() -> None:
    site_mode = "--site" in sys.argv
    audit_withheld_formulas_absent_from_current_tree()
    audit_puzzle_source_has_no_answer_key()
    audit_noindex_source_pages()
    if site_mode:
        audit_materialized_site()
    print("Challenge disclosure audit: PASS")


if __name__ == "__main__":
    main()
