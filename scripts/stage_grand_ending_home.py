from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")

    # Homepage directory is the durable cross-system entry surface. Global nav
    # is normalized later by harden_site.py, so new conceptual routes are also
    # linked from body content instead of depending on a one-off nav mutation.
    novel_entry = (
        '<li class="novel-entry"><a href="novel/">'
        '<strong>Bách Lâm · Lần Hồi Quy Thứ Một Triệu · Chương 1 HALF-CANON</strong>'
        '<span>Chương 1 đã được nâng thành PUBLIC HALF-CANON: sự kiện lõi tạo continuity, world build Việt Nam đầu thế kỷ XXI có Reality Anchor Ledger, còn các cơ chế sâu chưa đủ căn cứ vẫn giữ UNKNOWN.</span>'
        '</a></li>'
    )
    system_entry = (
        '<li class="conservation-system-entry"><a href="system.html">'
        '<strong>Hệ Bảo Toàn BL∞ · BL-CONSERVE</strong>'
        '<span>Bản đồ toàn hệ nối Reality, GiaTai, UNKNOWN, Dân chủ Học thuật, provenance, critique, verification, execution, publication và narrative mà không xóa identity, version hay lịch sử phản biện.</span>'
        '</a></li>'
    )
    oap_entry = (
        '<li class="open-academic-publishing-entry"><a href="open-academic-publishing.html">'
        '<strong>Công nghệ Xuất bản Tự do Học thuật · BL-OAP</strong>'
        '<span>Open entry ở publication surface nhưng không bình quân hóa epistemic weight: preservation queue tách khỏi verification queue, object-first review, provenance, Reality Veto và versioned republication.</span>'
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
    if 'class="conservation-system-entry"' not in text:
        entries += system_entry
    if 'class="open-academic-publishing-entry"' not in text:
        entries += oap_entry
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

    # If an older staged homepage happens to carry the former demo wording,
    # normalize it during the same pass. Fresh builds do not contain it.
    text = text.replace(
        'Bách Lâm · Lần Hồi Quy Thứ Một Triệu · Chương 1 DEMO',
        'Bách Lâm · Lần Hồi Quy Thứ Một Triệu · Chương 1 HALF-CANON',
    )
    text = text.replace(
        'Bản demo công khai, NON-CANON. Chương canon mới đang HOLD cho tới khi timeline dòng thời gian gốc đủ vững để khóa continuity.',
        'Chương 1 PUBLIC HALF-CANON: core continuity + sourced Reality Anchors + open UNKNOWN. Chương 2+ vẫn HOLD cho tới khi original-timeline spine đủ vững.',
    )

    INDEX.write_text(text, encoding="utf-8")
    print("BL∞ conservation + open academic publishing + HALF-CANON novel + world/UNKNOWN/Grand Ending linked from homepage: OK")


if __name__ == "__main__":
    main()
