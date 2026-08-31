from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")

    nav_anchor = '<a href="theory.html">Học thuyết</a>'
    nav_link = '<a href="grand-ending.html">Đại Kết Cục</a>'
    if nav_link not in text and nav_anchor in text:
        text = text.replace(nav_anchor, nav_anchor + nav_link, 1)

    entry = (
        '<li class="grand-ending-entry"><a href="grand-ending.html">'
        '<strong>Đại Kết Cục · UNKNOWN · Cosmic Optionality</strong>'
        '<span>Infinity ≠ Power; mô hình mở về áp lực hội tụ thấp-optionality, UNKNOWN, '
        'trí tuệ và sự sống như counter-pressure giữ thực tại còn khả năng sinh mới.</span>'
        '</a></li>'
    )
    directory_anchor = '<ul class="home-directory-grid">'
    if 'class="grand-ending-entry"' not in text:
        if directory_anchor not in text:
            raise RuntimeError("home-directory-grid anchor not found")
        text = text.replace(directory_anchor, directory_anchor + entry, 1)

    INDEX.write_text(text, encoding="utf-8")
    print("Grand Ending linked from homepage: OK")


if __name__ == "__main__":
    main()
