from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INDEX = SITE / "index.html"
SCIENCE_PAGE_SOURCE = ROOT / "public" / "science-constellation.html"
SCIENCE_REGISTRY_SOURCE = ROOT / "machine" / "external-science-constellation.json"
MTS_PAGE_SOURCE = ROOT / "public" / "mature-theory-synthesis.html"
MTS_REGISTRY_SOURCE = ROOT / "machine" / "bl-mature-theory-synthesis.json"
MTS_INTEGRATION_SOURCE = ROOT / "machine" / "bl-mts-integration.json"


def stage_external_science_constellation() -> None:
    if not SCIENCE_PAGE_SOURCE.exists():
        raise RuntimeError("public/science-constellation.html missing")
    if not SCIENCE_REGISTRY_SOURCE.exists():
        raise RuntimeError("machine/external-science-constellation.json missing")

    shutil.copy(SCIENCE_PAGE_SOURCE, SITE / "science-constellation.html")
    (SITE / "machine").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCIENCE_REGISTRY_SOURCE, SITE / "machine" / "external-science-constellation.json")

    world = SITE / "world.html"
    if world.exists():
        text = world.read_text(encoding="utf-8")
        marker = 'id="external-science-constellation"'
        if marker not in text:
            block = '''
<section class="chapter" id="external-science-constellation">
<h2>External Science Constellation: thế giới này không chỉ có phả hệ BL</h2>
<p class="first">Một world đủ trưởng thành phải va chạm với những phả hệ tri thức không thuộc mình. Standard Model, thuyết tương đối, Bell tests, LIGO, plate tectonics, Human Genome Project, CRISPR, AlphaFold, BRAIN Initiative, vật liệu 2D, quasicrystals, machine learning và những thất bại như LK-99 hay OPERA đều được giữ nguyên nguồn gốc khoa học bên ngoài BL.</p>
<p>BL∞ chỉ dùng chúng như <strong>constraint, đối trọng, bridge hoặc negative knowledge</strong> cho world-build. Điểm giống nhau không tạo tác quyền; điểm giao không tạo identity; và một science object không trở thành bằng chứng cho BL chỉ vì có cấu trúc tương tự.</p>
<div class="formula">External science
-> preserve external lineage
-> evidence status
-> intersection with BL
-> NON-intersection with BL
-> merge / bridge / hold / reject
-> world-build consequence
-> reality collision</div>
<p class="bridge"><a href="science-constellation.html">Mở External Science Constellation: atlas khoa học ngoài BL, lịch sử đảo chiều và negative knowledge →</a></p>
</section>
'''
            if "</article>" not in text:
                raise RuntimeError("world.html article close not found")
            text = text.replace("</article>", block + "</article>", 1)
            world.write_text(text, encoding="utf-8")


def stage_mature_theory_synthesis() -> None:
    if not MTS_PAGE_SOURCE.exists():
        raise RuntimeError("public/mature-theory-synthesis.html missing")
    if not MTS_REGISTRY_SOURCE.exists():
        raise RuntimeError("machine/bl-mature-theory-synthesis.json missing")
    if not MTS_INTEGRATION_SOURCE.exists():
        raise RuntimeError("machine/bl-mts-integration.json missing")

    shutil.copy(MTS_PAGE_SOURCE, SITE / "mature-theory-synthesis.html")
    (SITE / "machine").mkdir(parents=True, exist_ok=True)
    shutil.copy(MTS_REGISTRY_SOURCE, SITE / "machine" / "bl-mature-theory-synthesis.json")
    shutil.copy(MTS_INTEGRATION_SOURCE, SITE / "machine" / "bl-mts-integration.json")

    science = SITE / "science-constellation.html"
    if science.exists():
        text = science.read_text(encoding="utf-8")
        if 'id="bl-mts-compiler"' not in text and "</article>" in text:
            block = '''
<section class="section" id="bl-mts-compiler">
<h2>BL-MTS: giữ nguyên khoa học cũ, chỉ ghi cái mới sinh từ va chạm</h2>
<p>External Science Constellation bảo tồn atlas khoa học ngoài BL. <strong>BL-MTS</strong> là compiler riêng: ghi intersection, harmonization, disagreement và cannot-merge; chỉ object có <code>new_delta</code> và parent provenance mới được đi vào BL-emergent lineage.</p>
<p><a href="mature-theory-synthesis.html">Mở BL Mature-Theory Synthesis Branch →</a></p>
</section>
'''
            text = text.replace("</article>", block + "</article>", 1)
            science.write_text(text, encoding="utf-8")


def main() -> None:
    stage_external_science_constellation()
    stage_mature_theory_synthesis()
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
    regressor_entry = (
        '<li class="regressor-entry"><a href="regressor-proposition.html">'
        '<strong>Mệnh đề Kẻ Hồi Quy · BL-RP-FRC</strong>'
        '<span>Nhánh trực tiếp của BL∞ về future boundary, suy ngược ràng buộc, hành động hiện tại và Reality Veto; giữ ranh giới rõ giữa backward inference và backward physical signal.</span>'
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
    science_entry = (
        '<li class="external-science-entry"><a href="science-constellation.html">'
        '<strong>External Science Constellation · World-build Science Atlas</strong>'
        '<span>Khoa học ngoài phả hệ BL được giữ nguyên attribution: physics, quantum, cosmology, earth/climate, genomics, neuroscience, medicine, materials và computing; ghi rõ evidence status, điểm giao, điểm không giao và các claim đã bị thực tại bác.</span>'
        '</a></li>'
    )
    mts_entry = (
        '<li class="mature-theory-synthesis-entry"><a href="mature-theory-synthesis.html">'
        '<strong>BL-MTS · Nhánh Thống Hợp Học Thuyết Trưởng Thành</strong>'
        '<span>Giữ nguyên phả hệ theory family ngoài BL; lập intersection, harmonization, disagreement, cannot-merge; cấu trúc mới sinh từ va chạm chỉ vào BL-emergent lineage khi có new_delta + parent provenance + prior-art/Reality gate.</span>'
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
    if 'class="regressor-entry"' not in text:
        entries += regressor_entry
    if 'class="world-narrative-entry"' not in text:
        entries += world_entry
    if 'class="external-science-entry"' not in text:
        entries += science_entry
    if 'class="mature-theory-synthesis-entry"' not in text:
        entries += mts_entry
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
    print("BL∞ theory-first core + regressor + conservation + external science + BL-MTS + integration contract + open academic publishing + HALF-CANON novel + world/UNKNOWN/Grand Ending linked from homepage: OK")


if __name__ == "__main__":
    main()
