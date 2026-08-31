from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def normalize(text: str) -> str:
    text = text.replace(" — ", ": ")
    text = text.replace("—", ", ")
    text = text.replace(" – ", " · ")
    text = text.replace("–", "-")
    return text


def main() -> None:
    changed = 0
    for path in SITE.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        revised = normalize(original)
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            changed += 1
        if "—" in revised or "–" in revised:
            raise RuntimeError(f"long dash remains in {path.relative_to(SITE)}")
    print(f"Human-facing typography normalized: {changed} HTML files changed")


if __name__ == "__main__":
    main()
