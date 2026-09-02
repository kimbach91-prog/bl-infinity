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
MTS_INGESTION_SOURCE = ROOT / "machine" / "bl-mts-ingestion-map.json"
HYPOTHESIS_PAGE_SOURCE = ROOT / "public" / "hypotheses.html"
HYPOTHESIS_REGISTRY_SOURCE = ROOT / "machine" / "hypothesis-registry.json"
NOVEL_SCIENCE_WEAVE_SOURCE = ROOT / "machine" / "novel-global-science-weave.json"


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
    required = [
        MTS_PAGE_SOURCE,
        MTS_REGISTRY_SOURCE,
        MTS_INTEGRATION_SOURCE,
        MTS_INGESTION_SOURCE,
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise RuntimeError("BL-MTS source missing: " + ", ".join(missing))

    shutil.copy(MTS_PAGE_SOURCE, SITE / "mature-theory-synthesis.html")
    (SITE / "machine").mkdir(parents=True, exist_ok=True)
    shutil.copy(MTS_REGISTRY_SOURCE, SITE / "machine" / "bl-mature-theory-synthesis.json")
    shutil.copy(MTS_INTEGRATION_SOURCE, SITE / "machine" / "bl-mts-integration.json")
    shutil.copy(MTS_INGESTION_SOURCE, SITE / "machine" / "bl-mts-ingestion-map.json")

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


def stage_hypothesis_branch_and_science_weave() -> None:
    required = [HYPOTHESIS_PAGE_SOURCE, HYPOTHESIS_REGISTRY_SOURCE, NOVEL_SCIENCE_WEAVE_SOURCE]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise RuntimeError("BL-HYP/science-weave source missing: " + ", ".join(missing))

    shutil.copy(HYPOTHESIS_PAGE_SOURCE, SITE / "hypotheses.html")
    (SITE / "machine").mkdir(parents=True, exist_ok=True)
    shutil.copy(HYPOTHESIS_REGISTRY_SOURCE, SITE / "machine" / "hypothesis-registry.json")
    shutil.copy(NOVEL_SCIENCE_WEAVE_SOURCE, SITE / "machine" / "novel-global-science-weave.json")

    chapter = SITE / "novel" / "chapter-001.html"
    if not chapter.exists():
        raise RuntimeError("rendered Chapter 1 missing before science weave")
    text = chapter.read_text(encoding="utf-8")
    if 'id="global-science-continuity-weave"' not in text:
        marker = '<p>Ở đâu đó ngoài căn phòng, Internet đã đi vào Việt Nam từ trước khi Bách hiểu Internet là gì.'
        if marker not in text:
            raise RuntimeError("Chapter 1 science-weave insertion marker missing")
        block = '''
<section id="global-science-continuity-weave">
<h2>Khoa học ngoài kia không đứng yên chờ một đứa trẻ lớn lên</h2>
<p>Bách lớn lên trong một thời kỳ mà những thứ từng nằm sâu trong sách và phòng thí nghiệm liên tục tràn ra màn hình của người bình thường. Năm 2003, Human Genome Project khép lại mục tiêu chính của một bản tham chiếu bộ gene người; nhiều năm sau người ta vẫn tiếp tục lấp những khoảng trống còn lại. Một bản đồ rất lớn vừa hoàn thành không có nghĩa con người đã được giải thích xong.</p>
<p>Đến năm 2012, hai câu chuyện khác nhau cùng làm đường biên giữa <em>biết</em> và <em>làm được</em> dịch chuyển. Ở CERN, ATLAS và CMS công bố một hạt mới phù hợp với Higgs boson, thứ đã sống hàng thập kỷ trong lý thuyết trước khi máy gia tốc đủ mạnh để chạm vào nó bằng dữ liệu. Cũng trong năm ấy, CRISPR-Cas9 mở ra một con đường chỉnh sửa gene có thể lập trình: từ đọc một phần mã của sự sống sang can thiệp vào nó.</p>
<p>Năm 2015, LIGO ghi được GW150914; đầu 2016 thế giới nghe công bố về lần đầu gravitational waves được phát hiện trực tiếp. Những gợn của không-thời gian từng chỉ nằm trong phương trình trở thành tín hiệu trong máy đo. Bách không cần hiểu hết vật lý để nhận ra một pattern: đôi khi Reality không đổi, chỉ là nền văn minh cuối cùng cũng chế tạo được giác quan để nhìn phần trước đó nó không nhìn thấy.</p>
<p>Rồi máy học đi từ một ngành người ngoài khó hình dung thành hạ tầng len vào tìm kiếm, hình ảnh, ngôn ngữ và nghiên cứu. Đến 2024, Nobel Vật lý ghi nhận những nền tảng của machine learning bằng artificial neural networks; Nobel Hóa học cùng năm ghi nhận computational protein design và protein structure prediction. Một cỗ máy có thể dự đoán cấu trúc rất giỏi vẫn không làm thí nghiệm biến mất. Nó chỉ đẩy câu hỏi tiếp theo sang một biên mới.</p>
<p>Bách không coi những mốc ấy là bằng chứng cho bất kỳ học thuyết nào của mình. Chúng làm một việc khác: dạy cả một thế hệ rằng <strong>representation, prediction, observation và intervention là bốn ngưỡng khác nhau</strong>. Có thứ ta viết được trước khi đo được. Có thứ đo được trước khi hiểu hết. Có thứ dự đoán được trước khi điều khiển được. Và có những chỗ, sau tất cả, câu trả lời tốt nhất vẫn là: chưa biết.</p>
<p class="source">Reality anchors: <a href="https://www.genome.gov/human-genome-project">NHGRI · Human Genome Project</a> · <a href="https://home.cern/science/physics/higgs-boson">CERN · Higgs boson</a> · <a href="https://www.nobelprize.org/prizes/chemistry/2020/press-release/">Nobel · CRISPR</a> · <a href="https://ligo.org/science-summaries/gw150914/">LIGO · GW150914</a> · <a href="https://www.nobelprize.org/prizes/physics/2024/press-release/">Nobel Physics 2024</a> · <a href="https://www.nobelprize.org/prizes/chemistry/2024/press-release/">Nobel Chemistry 2024</a>.</p>
</section>

'''
        text = text.replace(marker, block + marker, 1)
        chapter.write_text(text, encoding="utf-8")


def main() -> None:
    stage_external_science_constellation()
    stage_mature_theory_synthesis()
    stage_hypothesis_branch_and_science_weave()
    text = INDEX.read_text(encoding="utf-8")

    root_entry = (
        '<li class="bl-infinity-root-entry"><a href="index.html">'
        '<strong>BL∞ · Toàn hệ</strong>'
        '<span>Root public surface của BL∞: Học thuyết, Giả thuyết, Tiểu thuyết, Reality–GiaTai–UNKNOWN, Regressor, hệ bảo toàn, khoa học ngoài BL, provenance và critique.</span>'
        '</a></li>'
    )
    hypothesis_entry = (
        '<li class="hypothesis-entry"><a href="hypotheses.html">'
        '<strong>Giả thuyết BL∞ · BL-HYP</strong>'
        '<span>Nhánh riêng cho các hypothesis hỗ trợ hệ; Theory ≠ Hypothesis ≠ Fiction và mọi promotion đều phải qua evidence, prior art, provenance và Reality Veto.</span>'
        '</a></li>'
    )
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
        '<span>UNKNOWN là contact frontier giữa cấu trúc hiện tại và độ mở BL∞; nối GiaTai/imagination, ontology genesis, false-known, cooperation, actualization và biên UNKNOWN sâu hơn.</span>'
        '</a></li>'
    )
    grand_entry = (
        '<li class="grand-ending-entry"><a href="grand-ending.html">'
        '<strong>Đại Kết Cục · BL∞ · UNKNOWN · Cosmic Optionality</strong>'
        '<span>Infinity != Power; phân biệt fixed infinity với B Infinity và mô hình sự sống/trí tuệ như counter-pressure trước terminal convergence thấp-generativity.</span>'
        '</a></li>'
    )
    directory_anchor = '<ul class="home-directory-grid">'
    if directory_anchor not in text:
        raise RuntimeError("home-directory-grid anchor not found")

    entries = ''
    if 'class="bl-infinity-root-entry"' not in text:
        entries += root_entry
    if 'class="hypothesis-entry"' not in text:
        entries += hypothesis_entry
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

    text = text.replace(
        'Bách Lâm · Lần Hồi Quy Thứ Một Triệu · Chương 1 DEMO',
        'Bách Lâm · Lần Hồi Quy Thứ Một Triệu · Chương 1 HALF-CANON',
    )
    text = text.replace(
        'Bản demo công khai, NON-CANON. Chương canon mới đang HOLD cho tới khi timeline dòng thời gian gốc đủ vững để khóa continuity.',
        'Chương 1 PUBLIC HALF-CANON: core continuity + sourced Reality Anchors + open UNKNOWN. Chương 2+ vẫn HOLD cho tới khi original-timeline spine đủ vững.',
    )

    INDEX.write_text(text, encoding="utf-8")
    print("BL∞ root + hypothesis branch + global science narrative weave + BL-MTS/world surfaces staged: OK")


if __name__ == "__main__":
    main()
