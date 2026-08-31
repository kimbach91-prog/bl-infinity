from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")

    nav_anchor = '<a href="theory.html">Học thuyết</a>'
    world_nav = '<a href="world.html">Bản kể</a>'
    novel_nav = '<a href="novel/">Tiểu thuyết</a>'
    unknown_nav = '<a href="unknown.html">UNKNOWN</a>'
    grand_nav = '<a href="grand-ending.html">Đại Kết Cục</a>'
    if nav_anchor in text:
        additions = ''
        if world_nav not in text:
            additions += world_nav
        if novel_nav not in text:
            additions += novel_nav
        if unknown_nav not in text:
            additions += unknown_nav
        if grand_nav not in text:
            additions += grand_nav
        if additions:
            text = text.replace(nav_anchor, nav_anchor + additions, 1)

    novel_entry = (
        '<li class="novel-entry"><a href="novel/">'
        '<strong>Bách Lâm · Lần Hồi Quy Thứ Một Triệu · Tiểu thuyết dài kỳ</strong>'
        '<span>Fiction surface riêng. Chương 1: Đại Kết Cục Thứ Một Nghìn. Những gì truyện chưa kể sẽ không được mục lục kể hộ.</span>'
        '</a></li>'
    )
    world_entry = (
        '<li class="world-narrative-entry"><a href="world.html">'
        '<strong>Bản nghiên cứu kể chuyện BL∞</strong>'
        '<span>Dành cho người muốn đào sâu hơn vào các ý tưởng và quan hệ nghiên cứu phía sau world build; không phải spoiler guide của tiểu thuyết.</span>'
        '</a></li>'
    )
    unknown_entry = (
        '<li class="unknown-doctrine-entry"><a href="unknown.html">'
        '<strong>Học thuyết UNKNOWN · Trường Chưa-biết Sinh thành của BL∞</strong>'
        '<span>UNKNOWN là contact frontier giữa cấu trúc hiện tại và độ mở BL∞; '
        'nối GiaTai/imagination, ontology genesis, false-known, cooperation, actualization và biên UNKNOWN sâu hơn.</span>'
        '</a></li>'
    )
    grand_entry = (
        '<li class="grand-ending-entry"><a href="grand-ending.html">'
        '<strong>Đại Kết Cục · BL∞ · UNKNOWN · Cosmic Optionality</strong>'
        '<span>Infinity != Power; phân biệt fixed infinity với B Infinity và mô hình sự sống/trí tuệ như counter-pressure '
        'trước terminal convergence thấp-generativity.</span>'
        '</a></li>'
    )
    directory_anchor = '<ul class="home-directory-grid">'
    if directory_anchor not in text:
        raise RuntimeError("home-directory-grid anchor not found")

    entries = ''
    if 'class="novel-entry"' not in text:
        entries += novel_entry
    if 'class="world-narrative-entry"' not in text:
        entries += world_entry
    if 'class="unknown-doctrine-entry"' not in text:
        entries += unknown_entry
    if 'class="grand-ending-entry"' not in text:
        entries += grand_entry
    if entries:
        text = text.replace(directory_anchor, directory_anchor + entries, 1)

    INDEX.write_text(text, encoding="utf-8")
    print("BL∞ novel + world narrative + UNKNOWN Doctrine + Grand Ending linked from homepage: OK")


if __name__ == "__main__":
    main()
