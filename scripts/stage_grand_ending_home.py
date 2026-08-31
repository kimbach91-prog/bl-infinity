from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")

    nav_anchor = '<a href="theory.html">Học thuyết</a>'
    unknown_nav = '<a href="unknown.html">UNKNOWN</a>'
    grand_nav = '<a href="grand-ending.html">Đại Kết Cục</a>'
    if nav_anchor in text:
        additions = ''
        if unknown_nav not in text:
            additions += unknown_nav
        if grand_nav not in text:
            additions += grand_nav
        if additions:
            text = text.replace(nav_anchor, nav_anchor + additions, 1)

    unknown_entry = (
        '<li class="unknown-doctrine-entry"><a href="unknown.html">'
        '<strong>Học thuyết UNKNOWN · Không gian Chưa-biết Mở</strong>'
        '<span>UNKNOWN không chỉ là thiếu đáp án: quan hệ observer–model–reality–history; '
        'unknown-unknown, false-known, future chưa thành thực tại, optionality và năng lực trí tuệ sống sót qua điều chưa biết.</span>'
        '</a></li>'
    )
    grand_entry = (
        '<li class="grand-ending-entry"><a href="grand-ending.html">'
        '<strong>Đại Kết Cục · UNKNOWN · Cosmic Optionality</strong>'
        '<span>Infinity ≠ Power; mô hình mở về áp lực hội tụ thấp-optionality, UNKNOWN, '
        'trí tuệ và sự sống như counter-pressure giữ thực tại còn khả năng sinh mới.</span>'
        '</a></li>'
    )
    directory_anchor = '<ul class="home-directory-grid">'
    if directory_anchor not in text:
        raise RuntimeError("home-directory-grid anchor not found")

    entries = ''
    if 'class="unknown-doctrine-entry"' not in text:
        entries += unknown_entry
    if 'class="grand-ending-entry"' not in text:
        entries += grand_entry
    if entries:
        text = text.replace(directory_anchor, directory_anchor + entries, 1)

    INDEX.write_text(text, encoding="utf-8")
    print("UNKNOWN Doctrine + Grand Ending linked from homepage: OK")


if __name__ == "__main__":
    main()
