# Bootstrap prompt cho mô hình tiếp theo

Tôi đang tiếp tục dự án **BL∞ / Bach Lam Infinity Proposition**, repository `kimbach91-prog/bl-infinity`.

Trước khi trả lời hay sửa code, hãy đọc toàn bộ `handoff/BL_INFINITY_HANDOFF_2026-08-29.md`, sau đó audit các source được chỉ định trong đó. Không lấy website public hiện tại làm nguồn đầy đủ nhất.

Nhiệm vụ của bạn là tiếp quản research object và chuẩn bị **v0.3 semantic rebuild**, không phát minh lại từ đầu.

Các nguyên tắc bắt buộc:

1. Phân biệt canonical hiện hành, historical origin, legacy alias, superseded formulation, optional/speculative extension, attack inventory và implementation.
2. Tạo canonical precedence/identity ledger trước khi viết site mới.
3. Reconcile lỗi axiom ID: `content/03` và `claims/claims.json` hiện có numbering không đồng nhất, đặc biệt A05/A-005.
4. Reconcile legacy `Semantic Gravity / BL-SG` với canonical successor `BL-ORBIT`.
5. Không render toàn bộ `content/*.md` thành một theory page phẳng.
6. Không được làm mất các correction quan trọng:
   - representation tồn tại không entail referent actual;
   - inconceivable không entail impossible;
   - conceivable không entail reachable/actual;
   - not-actual không entail unreachable;
   - infinite time không đủ nếu accessibility/dynamics không phù hợp;
   - open ontology không entail arbitrary entities;
   - prior-art(component) không entail prior-art(system), nhưng prior system isomorphic vẫn có thể defeat novelty;
   - independent derivation khác historical priority;
   - system complexity/indexing/AI consensus không entail truth.
7. Toán học phải có semantics, assumptions và proof-status; dùng MathJax/KaTeX hoặc tương đương.
8. Mỗi core claim phải trở thành rich claim object: statement, type/status, assumptions, formalism, derivation, explanation, boundaries, falsifiers, dependencies, critique history, provenance, version delta.
9. Attack matrix phải có resolution ledger; không dump objection đã được patch như thể lỗi còn mở.
10. Tách 3 tầng public rõ ràng:
    - BL∞ core ontology/epistemology/formalization;
    - Optimizer cognition/method;
    - BLOK/BL-AEGIS research infrastructure.
11. Giữ provenance. Không rewrite lịch sử thành truyện trơn tru giả tạo. Nếu raw transcript không có thì ghi rõ reconstructed.
12. Chưa bump version cho tới khi semantic migration và audit mới pass.

Đầu ra đầu tiên tôi muốn từ bạn:

A. Một **semantic diff report** có bảng: object → old formulation → objection → corrected formulation → canonical status → source.

B. Một **canonical ID migration table**.

C. Một **target information architecture** cho site v0.3.

D. Một **rich claim schema** và chọn 5 claim lõi để dựng mẫu cực chi tiết trước.

E. Một plan sửa build system sao cho human HTML, machine JSON/JSON-LD và claim registry được generate từ một canonical structured source, tránh drift.

F. Chạy adversarial audit vào chính plan của bạn trước khi commit.

Không làm kiểu “tóm tắt cho đẹp”. Mục tiêu là giữ độ phân giải của cả quá trình suy luận, phản chứng và formalization.
