#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "research/human-development/kevin-nt/studio/index.html"
text = P.read_text(encoding="utf-8")

# Surface the methodology as a reader-facing section, not backstage vocabulary.
if '<a href="#case-method">Phương pháp</a>' not in text:
    text = text.replace(
        '<a href="#benchmark">Ứng dụng thật</a><a href="#sources">Nguồn</a>',
        '<a href="#benchmark">Ứng dụng thật</a><a href="#case-method">Phương pháp</a><a href="#sources">Nguồn</a>'
    )

if '<a href="#case-method">Case study phương pháp BL∞ + LLM Agent</a>' not in text:
    text = text.replace(
        '<li><a href="#protocol">Cách hai bên tranh luận</a></li><li><a href="#sources">Nguồn công khai</a></li>',
        '<li><a href="#protocol">Cách hai bên tranh luận</a></li><li><a href="#case-method">Case study phương pháp BL∞ + LLM Agent</a></li><li><a href="#sources">Nguồn công khai</a></li>'
    )

CASE = '''<section id="case-method"><span class="role evidence">Case study phương pháp · BL∞ Whole-System Intelligence</span><h2>12. Dùng toàn hệ BL∞ để điều tra nguồn mở, lập luận sâu và xuất bản bằng LLM Agent</h2><p>Trang Kevin Research Studio đồng thời là một <strong>case study về phương pháp dùng toàn hệ BL∞ để tổng hợp tình báo nguồn mở về một con người</strong>. “Tình báo” ở đây được dùng theo nghĩa kỹ thuật: thu thập, chuẩn hóa, đối chiếu và diễn giải thông tin mà chủ thể đã công khai hoặc cho phép sử dụng. Nó <strong>không bao gồm theo dõi bí mật, xâm nhập tài khoản, thu thập dữ liệu riêng tư, suy diễn sức khỏe hay đời sống kín</strong>.</p><p>Đối tượng của case này là Kevin T.N. Mục tiêu không phải dựng một “hồ sơ con người hoàn chỉnh”, mà là kiểm tra xem một hệ LLM-agent có thể đi từ corpus công khai tới một mô hình nghiên cứu có provenance, contradiction, UNKNOWN, falsifier, benchmark và Right of Reply như thế nào.</p><div class="claim-grid"><div class="claim"><div class="label">Đầu vào hợp lệ</div><p>Repo, dataset, paper, README, benchmark, version history, bài viết và phát ngôn công khai; dữ liệu riêng chỉ dùng khi có quyền phù hợp.</p></div><div class="claim"><div class="label">Đầu ra mong muốn</div><p>Một mô hình có thể kiểm tra: Kevin đang làm gì, cơ chế nào lặp lại, điểm nào chỉ là suy luận, artifact nào có giá trị ứng dụng và claim nào cần mở lại.</p></div></div><h3>12.1. Chu trình điều tra nguồn mở của case</h3><div class="matrix-wrap"><table class="matrix"><thead><tr><th>Bước</th><th>BL∞ làm gì</th><th>Điều kiện kiểm soát</th></tr></thead><tbody><tr><td>1. Xác định chủ thể</td><td>Resolve Kevin T.N / Tùng Nguyễn / jkdkr2439 và tách khỏi các cá nhân trùng tên.</td><td>Identity chỉ được nối khi có dấu vết công khai đủ mạnh; phần chưa chắc giữ UNKNOWN.</td></tr><tr><td>2. Thu thập corpus</td><td>Lập chỉ mục GitHub, Hugging Face, paper, dataset, benchmark, version history và các trang công khai liên quan.</td><td>Chỉ nguồn công khai hoặc được cấp quyền; không mở rộng sang dữ liệu đời tư chỉ vì có thể tìm thấy.</td></tr><tr><td>3. Chuẩn hóa provenance</td><td>Gắn artifact, thời gian, tác giả, lineage, bản sửa, source URL và trạng thái evidence.</td><td>Similarity không tự chứng minh derivation; chronology và fingerprint phải tách riêng.</td></tr><tr><td>4. Phân rã lập luận</td><td>Tách observation, inference, hypothesis, decision, claim boundary, contradiction và UNKNOWN.</td><td>Một câu “nghe hợp lý” không được nâng thành fact nếu không có source.</td></tr><tr><td>5. Phân tích đa lát cắt</td><td>Dùng toàn hệ theo bài toán: frame, mechanism, time trajectory, application, failure, repair, attribution, collaboration và development frontier.</td><td>Không chấm điểm con người bằng một scalar duy nhất; benchmark tập trung vào artifact và hành vi nghiên cứu quan sát được.</td></tr><tr><td>6. Adversarial synthesis</td><td>Cho các cách giải thích cạnh tranh cùng tồn tại, tìm counterexample và điều kiện làm mỗi model sai.</td><td>Reality Veto cao hơn narrative của Bách hoặc Kevin.</td></tr><tr><td>7. Human-development interpretation</td><td>Chuyển kết quả sang câu hỏi thực dụng: năng lực nào nên tăng, blind spot nào cần test, resource nào giúp ích.</td><td>Development không đồng nghĩa control; Kevin có quyền chấp nhận, sửa hoặc bác diễn giải.</td></tr><tr><td>8. Xuất bản và phản biện</td><td>LLM Agent biên tập long-form, tạo cấu trúc web, metadata, favicon/cover, commit, CI và Pages release.</td><td>Mọi public claim giữ Right of Reply, revision history và attribution.</td></tr></tbody></table></div><h3>12.2. BL∞ được dùng như một hệ phối hợp, không phải một prompt lớn</h3><p>Case này huy động các năng lực BL theo vai trò khác nhau. <strong>BL∞</strong> giữ biên known/unknown và cấu trúc vấn đề. <strong>BLEE</strong> giữ đa quan sát và trọng lượng bằng chứng. <strong>Reality Veto</strong> buộc model sửa khi nguồn hoặc kết quả thực mâu thuẫn. <strong>BL-ADN/provenance</strong> giữ lineage và attribution. Các lớp repair, execution, benchmark và cooperation biến phân tích thành artifact công khai có thể phản biện.</p><p>Nguyên tắc vận hành là <strong>smallest sufficient stack</strong>: không bật toàn bộ module chỉ để làm hệ trông phức tạp. Mỗi module chỉ được dùng khi nó giải một failure mode cụ thể của bài toán.</p><h3>12.3. Xuất bản tự động bằng LLM Agent: claim chính xác là gì?</h3><div class="speaker evidence"><span class="role evidence">Trạng thái công bố hiện tại</span><p>Pipeline của case cho phép một chỉ dẫn cấp mục tiêu từ người vận hành được chuyển thành chuỗi thực thi end-to-end bằng LLM Agent và toolchain do BL phát triển/điều phối: đọc nguồn, tổng hợp, viết, sửa HTML, tạo metadata/ảnh social, commit, chạy CI, kiểm tra Pages và phát hành. <strong>“Tự động” ở đây không có nghĩa không còn human authority</strong>: Bách Lâm vẫn đặt mục tiêu, biên công bố và quyền chốt; Kevin giữ quyền phản biện đối với phần nói về Kevin.</p></div><p>Case này vì vậy kiểm tra hai thứ cùng lúc: <strong>chất lượng lập luận về một chủ thể thật</strong> và <strong>khả năng của một agentic research pipeline biến nghiên cứu thành artifact công khai có kiểm toán mà không cần người vận hành tự tay làm từng bước kỹ thuật</strong>.</p><div class="test"><strong>Benchmark độc lập sẽ công bố sau</strong>Hiện tại chưa có benchmark độc lập đã hoàn tất để chứng minh pipeline BL∞ + LLM Agent vượt các baseline khác. Bản công khai chỉ ghi nhận đây là một hệ đang vận hành và đã tạo ra artifact/commit/deployment cụ thể. Benchmark sắp tới cần có evaluator độc lập, task set cố định, baseline công khai, tiêu chí chất lượng nguồn, độ chính xác attribution, hallucination rate, correction latency, human effort, thời gian, chi phí và khả năng tái lập.</div><h3>12.4. Những metric cần công bố khi benchmark độc lập</h3><ul><li><strong>Source precision / recall:</strong> tìm đúng bao nhiêu nguồn quan trọng và bỏ sót bao nhiêu.</li><li><strong>Attribution accuracy:</strong> claim nào gắn đúng người, đúng artifact, đúng chronology.</li><li><strong>OBS → INFER error rate:</strong> tần suất agent biến suy luận thành dữ kiện.</li><li><strong>Contradiction retention:</strong> có giữ được nhánh mâu thuẫn thay vì ép hợp nhất sớm không.</li><li><strong>Correction responsiveness:</strong> khi Kevin hoặc reviewer đưa nguồn mạnh hơn, model sửa nhanh và đúng tới đâu.</li><li><strong>Real application value:</strong> sản phẩm phái sinh có tạo utility đo được ngoài việc “viết được một bài dài” hay không.</li><li><strong>Human effort:</strong> số phút can thiệp của người vận hành từ yêu cầu cấp cao tới bản phát hành hoàn chỉnh.</li><li><strong>Reproducibility:</strong> cùng corpus và policy, một run độc lập có tái tạo được kết luận lõi và provenance không.</li></ul><div class="speaker kevin"><span class="role kevin">Kevin và reviewer có thể phản biện chính phương pháp này</span><p>Nếu Kevin cho rằng BL đã chọn sai nguồn, mô hình hóa sai chronology, bỏ qua một artifact quan trọng, dùng metric không công bằng hoặc gọi “tự động” quá rộng, phản biện đó được xem là dữ liệu kiểm thử của chính phương pháp. Case study chỉ có giá trị nếu nó cho phép đối tượng nghiên cứu làm hệ nghiên cứu phải sửa.</p></div></section>'''

if 'id="case-method"' not in text:
    marker = '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>12. Những nguồn công khai chính đang được dùng</h2>'
    if marker not in text:
        raise SystemExit('Kevin Studio source marker not found')
    text = text.replace(
        marker,
        CASE + '\n<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>13. Những nguồn công khai chính đang được dùng</h2>'
    )
else:
    text = text.replace(
        '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>12. Những nguồn công khai chính đang được dùng</h2>',
        '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>13. Những nguồn công khai chính đang được dùng</h2>'
    )

text = text.replace(
    'Mọi diễn giải về Kevin trên trang này đều mở cho phản biện và sửa đổi.',
    'Mọi diễn giải về Kevin và mọi claim về phương pháp BL∞/LLM Agent trên trang này đều mở cho phản biện, kiểm toán và sửa đổi.'
)

required = (
    'id="case-method"',
    'Case study phương pháp · BL∞ Whole-System Intelligence',
    'Benchmark độc lập sẽ công bố sau',
    'Human effort:',
    '13. Những nguồn công khai chính đang được dùng',
)
for marker in required:
    if marker not in text:
        raise SystemExit(f'Missing Kevin intelligence case marker: {marker}')

P.write_text(text, encoding="utf-8")
print('Kevin BL∞ intelligence + LLM Agent case study patch: PASS')
