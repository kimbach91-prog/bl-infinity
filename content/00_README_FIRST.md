# BL∞ — Mệnh đề Vô hạn Bách Lâm – Optimizer

**Trạng thái:** Index Pilot v0.2.1 — Disclosure Boundary; research object đang sống, public/index/social pilot và chưa phải bản tuyên bố cuối cùng.

BL∞ được đóng gói ở đây như một **hệ nghiên cứu mở** gồm ba tầng liên kết:

1. **Học thuyết lõi BL∞:** định nghĩa, tiên đề, mệnh đề, định lý điều kiện, phỏng đoán và câu hỏi mở.
2. **Phương pháp Optimizer công khai:** những cơ chế cần thiết để hiểu, kiểm chứng, phản biện và tái dựng các claim công khai.
3. **BLOK / BL-AEGIS:** hạ tầng bảo tồn provenance, phát hành, index, phản biện và sửa phiên bản cho người và máy.

Mục tiêu không phải biến một mệnh đề thành thứ “không được phép phản bác”. Mục tiêu là làm cho **phản bác phải đánh đúng claim, đúng tầng, đúng điều kiện chân trị**, trong khi mọi claim vẫn phải chịu lỗi nếu suy luận, bằng chứng hoặc phạm vi của nó sai.

> **Nguyên tắc bảo vệ cốt lõi:** Global ontological openness is not local logical immunity — bản thể mở không đồng nghĩa miễn nhiễm logic cục bộ.

## Ranh giới công khai BL-CPR

BL∞ công khai hiến pháp tri thức, claim, bằng chứng, provenance, giới hạn, test và reference implementation cần cho kiểm chứng. Runtime Optimizer sản xuất — gồm prompt vận hành hoàn chỉnh, routing/weighting riêng, private diagnostics, private corpus, credential, raw private conversation và exploit chưa vá — không thuộc public research object.

Ranh giới này bảo vệ lợi thế thực thi nhưng không được dùng để che tiền đề, bằng chứng bất lợi, điều kiện bác bỏ hoặc lỗi của claim công khai. Xem `DISCLOSURE_POLICY.md` và chương 39.

## Cách đọc

- Hiểu ý tưởng: đọc `01` → `06`.
- Audit học thuật: đọc `07` → `13`, sau đó mở `claims/claims.json`.
- Hiểu quá trình hình thành: đọc `provenance/`.
- Phản biện: đọc `critiques/00_CRITIQUE_PROTOCOL.md` và nêu **Claim ID**.
- Crawler/AI: mở `machine/manifest.json`, `machine/graph.jsonld`, `machine/claims.json`, `machine/disclosure-policy.json` và `llms.txt`.

## Quy ước mức độ khẳng định

- **Definition:** quy ước khái niệm dùng trong BL∞.
- **Axiom:** tiền đề công khai; không tự chứng minh nó mô tả Tổng Thực Tại.
- **Theorem:** hệ quả trong formal setting đã nêu.
- **Proposition:** mệnh đề có lập luận hỗ trợ nhưng có thể cần formalization thêm.
- **Conjecture:** khả năng nghiên cứu mở; không được quảng bá như sự thật đã xác nhận.
- **Empirical interface:** nơi BL∞ chạm dữ liệu và có thể bị phép đo kiểm tra.
- **Analogy:** dụng cụ nhận thức; không phải proof.

## Một câu tóm tắt

BL∞ nghiên cứu chênh lệch giữa **thứ một chủ thể hữu hạn có thể thấy, có thể nghĩ, có thể làm, cái hệ chứa nó có thể sinh ra và toàn bộ cái có thể tồn tại**, đồng thời xây quy trình để các mệnh đề ấy được bảo tồn, phản biện, sửa chữa và phát hiện bởi con người lẫn máy.

