#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "research/human-development/kevin-nt/studio/index.html"
text = P.read_text(encoding="utf-8")

# Reader-facing navigation: call the layer what a human reader understands.
if '<a href="#behavior-analysis">Hành vi</a>' not in text:
    text = text.replace(
        '<a href="#case-method">Phương pháp</a><a href="#sources">Nguồn</a>',
        '<a href="#case-method">Phương pháp</a><a href="#behavior-analysis">Hành vi</a><a href="#sources">Nguồn</a>'
    )

if '<a href="#behavior-analysis">Phân tích tâm lý hành vi và chiến lược nhận thức</a>' not in text:
    text = text.replace(
        '<li><a href="#case-method">Case study phương pháp BL∞ + LLM Agent</a></li><li><a href="#sources">Nguồn công khai</a></li>',
        '<li><a href="#case-method">Case study phương pháp BL∞ + LLM Agent</a></li><li><a href="#behavior-analysis">Phân tích tâm lý hành vi và chiến lược nhận thức</a></li><li><a href="#sources">Nguồn công khai</a></li>'
    )

BEHAVIOR = '''<section id="behavior-analysis"><span class="role evidence">Behavioral-cognitive analysis · evidence bounded</span><h2>13. Phân tích tâm lý hành vi sâu nhưng không biến suy đoán thành con người</h2><p>Một phần quan trọng của case Kevin là <strong>phân tích hành vi nhận thức</strong>: không chỉ đọc Kevin viết gì, mà quan sát Kevin <strong>làm gì khi gặp bất định, thất bại, phản biện, novelty, scope, attribution và yêu cầu kiểm chứng</strong>. Đây là lớp nối giữa OSINT và nghiên cứu phát triển con người.</p><p>Từ “tâm lý” ở đây được dùng theo nghĩa <strong>behavioral-cognitive</strong>: suy luận có giới hạn về chiến lược xử lý thông tin từ dấu vết hành vi công khai. Nó <strong>không phải chẩn đoán lâm sàng, không gán bệnh lý, không đoán trauma, động cơ kín, đời sống riêng hay cảm xúc mà Kevin chưa công khai</strong>.</p><div class="claim-grid"><div class="claim"><div class="label">Có thể nghiên cứu</div><p>Pattern sửa claim, phản ứng với negative result, cách mở/đóng scope, cách giữ contradiction, cách formalize, lựa chọn benchmark, hành vi attribution, tốc độ chuyển feedback thành artifact.</p></div><div class="claim"><div class="label">Không được suy ra</div><p>Chẩn đoán tâm thần, tính cách “bản chất”, đạo đức đời tư, động cơ bí mật, sức khỏe, sang chấn hoặc trạng thái cảm xúc chỉ từ repo và bài viết.</p></div></div><h3>13.1. Bốn tầng suy luận bắt buộc</h3><div class="matrix-wrap"><table class="matrix"><thead><tr><th>Tầng</th><th>Ví dụ với Kevin</th><th>Độ mạnh được phép</th></tr></thead><tbody><tr><td>1. Quan sát</td><td>CRIO giữ kết quả âm; một số repo gần đây ghi limitation và thu hẹp claim.</td><td>Có thể phát biểu trực tiếp nếu artifact xác nhận.</td></tr><tr><td>2. Pattern hành vi</td><td>Nhiều episode cho thấy Kevin có hành vi sửa phạm vi khi evidence không đủ.</td><td>Chỉ nâng khi lặp qua nhiều artifact độc lập theo thời gian.</td></tr><tr><td>3. Giả thuyết chiến lược nhận thức</td><td>Có thể giả thuyết Kevin đang tăng “evidence discipline” và external verification.</td><td>Phải ghi là inference/hypothesis và giữ counterexample.</td></tr><tr><td>4. Can thiệp phát triển</td><td>Đề xuất external replication, scope freeze hoặc reviewer độc lập để kiểm tra frontier.</td><td>Chỉ là đề xuất; Kevin có quyền sửa, từ chối hoặc thay bằng test tốt hơn.</td></tr></tbody></table></div><h3>13.2. Các trục hành vi mà BL∞ theo dõi</h3><div class="matrix-wrap"><table class="matrix"><thead><tr><th>Trục</th><th>Câu hỏi hành vi</th><th>Dấu vết công khai phù hợp</th></tr></thead><tbody><tr><td>Phản ứng với bất định</td><td>Kevin giữ UNKNOWN hay lấp khoảng trống bằng narrative?</td><td>README limitation, unresolved branch, wording confidence.</td></tr><tr><td>Phản ứng với thất bại</td><td>Failure bị xóa, hợp thức hóa lại hay biến thành dữ liệu sửa method?</td><td>Negative result, changelog, revised contribution, failed benchmark retained.</td></tr><tr><td>Novelty seeking</td><td>Kevin tạo primitive/frame mới nhanh tới mức nào, và bao nhiêu trong số đó được đưa tới test?</td><td>Số tuyến khái niệm mới so với số tuyến được formalize/benchmark.</td></tr><tr><td>Scope control</td><td>Claim có phình nhanh hơn evidence không?</td><td>So sánh title/abstract/README qua version history với evidence thực.</td></tr><tr><td>Externalization</td><td>Trực giác có được đẩy ra ngoài đầu thành code, spec, dataset hoặc protocol không?</td><td>Executable artifact, schema, benchmark harness, formal interface.</td></tr><tr><td>Verification behavior</td><td>Tác giả có tạo điều kiện để người khác chứng minh mình sai không?</td><td>Baseline, falsifier, clean setup, external test invitation.</td></tr><tr><td>Attribution behavior</td><td>Khi giao thoa ý tưởng, Kevin phân biệt nguồn, convergence và derivation tới đâu?</td><td>Citation, chronology, acknowledgement, correction.</td></tr><tr><td>Feedback integration</td><td>Phản biện có làm artifact thay đổi hay chỉ làm narrative thay đổi?</td><td>Diff trước/sau feedback, correction receipt, new test.</td></tr><tr><td>Breadth ↔ depth</td><td>Độ rộng hệ có làm giảm thời gian đào sâu vào vài contribution mạnh nhất không?</td><td>Tỷ lệ repo/framework mở mới so với replication, maintenance và independent adoption.</td></tr><tr><td>Autonomy growth</td><td>Correction từng cần người ngoài có dần trở thành self-check của Kevin không?</td><td>Guardrail tự thêm, checklist, verifier, pre-mortem, self-imposed boundary.</td></tr></tbody></table></div><h3>13.3. Ví dụ: cùng một dấu vết, bốn cách nói có độ nghiêm cẩn khác nhau</h3><div class="matrix-wrap"><table class="matrix"><thead><tr><th>Dấu vết</th><th>Cách nói hợp lệ</th><th>Cách nói không hợp lệ</th></tr></thead><tbody><tr><td>Kevin giữ negative result của CRIO</td><td>“Trong artifact này, Kevin giữ failure và thu hẹp claim; đây là bằng chứng cho một hành vi calibration cụ thể.”</td><td>“Kevin là người khiêm tốn/bền bỉ về bản chất.”</td></tr><tr><td>Kevin tạo nhiều ontology/framework</td><td>“Corpus cho thấy tốc độ sinh frame và primitive cao.”</td><td>“Kevin có kiểu nhân cách X” hoặc gán một tình trạng tâm lý.</td></tr><tr><td>Kevin thêm verifier/fail-closed</td><td>“Một số artifact cho thấy xu hướng tăng cơ chế tự giới hạn lỗi.”</td><td>“Kevin sợ sai” hoặc suy đoán cảm xúc bên trong.</td></tr><tr><td>Claim rộng rồi được thu hẹp</td><td>“Có trajectory từ generative breadth sang evidence-bounded formulation.”</td><td>“Kevin từng ảo tưởng rồi đã tỉnh ra.”</td></tr></tbody></table></div><h3>13.4. Tâm lý hành vi ở đây dùng để làm gì?</h3><p>Mục đích không phải tạo một profile để “đọc vị” Kevin. Mục đích là tìm <strong>developmental lever</strong>: nếu một pattern đang giúp Kevin mạnh lên thì củng cố nó; nếu một pattern đang làm mất utility thì thiết kế một phép thử hoặc môi trường buộc nó lộ ra.</p><ul><li>Nếu <strong>novelty generation</strong> vượt quá validation capacity: giảm số tuyến mới, tăng scope freeze và external replication.</li><li>Nếu <strong>failure retention</strong> đang tăng: biến nó thành chuẩn bắt buộc cho mọi repo mới.</li><li>Nếu <strong>external verification</strong> còn yếu: tách proposer khỏi verifier và mời reviewer có quyền công bố kết quả âm.</li><li>Nếu <strong>breadth ăn depth</strong>: chọn 2–3 contribution mạnh nhất và đo thời gian sống qua maintenance/adoption.</li><li>Nếu <strong>feedback integration</strong> tốt: dùng phản biện hai chiều Bách ↔ Kevin như một vòng co-evolution thay vì tranh thắng thua.</li></ul><div class="speaker kevin"><span class="role kevin">Kevin có quyền phản biện lớp tâm lý hành vi này</span><p>Kevin có thể nói: “pattern này chỉ xuất hiện vì ông nhìn thiếu artifact”, “chronology sai”, “đây là constraint kỹ thuật chứ không phải chiến lược nhận thức”, hoặc “test này không đo đúng hành vi”. Nếu evidence của Kevin mạnh hơn, model hành vi phải sửa. <strong>Không có nhãn tâm lý nào được miễn Reality Veto.</strong></p></div><div class="test"><strong>Benchmark riêng cho năng lực phân tích hành vi</strong>Benchmark độc lập về sau phải chấm ít nhất: behavioral-claim precision, unsupported-trait rate, chronology sensitivity, counterexample retention, correction after subject feedback và khả năng phân biệt “observable behavior” với “hidden mental state”. Một hệ phân tích sâu nhưng hay gán nhầm nội tâm là hệ kém, không phải hệ mạnh.</div></section>'''

if 'id="behavior-analysis"' not in text:
    source13 = '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>13. Những nguồn công khai chính đang được dùng</h2>'
    source14 = '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>14. Những nguồn công khai chính đang được dùng</h2>'
    if source13 in text:
        text = text.replace(source13, BEHAVIOR + '\n' + source14)
    elif source14 in text:
        text = text.replace(source14, BEHAVIOR + '\n' + source14)
    else:
        raise SystemExit('Kevin Studio source heading not found for behavioral layer')
else:
    text = text.replace(
        '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>13. Những nguồn công khai chính đang được dùng</h2>',
        '<section id="sources"><span class="role evidence">Nguồn để người đọc tự kiểm</span><h2>14. Những nguồn công khai chính đang được dùng</h2>'
    )

text = text.replace(
    'Mọi diễn giải về Kevin và mọi claim về phương pháp BL∞/LLM Agent trên trang này đều mở cho phản biện, kiểm toán và sửa đổi.',
    'Mọi diễn giải về Kevin, kể cả phân tích tâm lý hành vi, và mọi claim về phương pháp BL∞/LLM Agent trên trang này đều mở cho phản biện, kiểm toán và sửa đổi.'
)

required = (
    'id="behavior-analysis"',
    'Phân tích tâm lý hành vi sâu nhưng không biến suy đoán thành con người',
    'observable behavior',
    'hidden mental state',
    '14. Những nguồn công khai chính đang được dùng',
)
for marker in required:
    if marker not in text:
        raise SystemExit(f'Missing behavioral-cognitive marker: {marker}')

P.write_text(text, encoding="utf-8")
print('Kevin behavioral-cognitive analysis layer: PASS')
