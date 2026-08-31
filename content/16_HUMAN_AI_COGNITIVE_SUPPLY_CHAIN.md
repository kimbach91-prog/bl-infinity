# 16 — Chuỗi cung ứng nhận thức Người + AI

Nghiên cứu hiện đại không phải hoạt động của bộ não cô lập. BL-CSC mô hình hóa:

\[
ResearchCapacity=HumanGenerator\times ToolNetwork\times KnowledgeAccess\times Compute\times Feedback
\]

Trong một workflow BL∞:

**Con người** có thể giữ vai trò chính ở conceptual origin, chọn vấn đề, định nghĩa mục tiêu, đánh giá ý nghĩa, quyết định premise và chịu trách nhiệm kết luận.

**LLM** có thể đóng vai formalizer, retrieval assistant, adversarial engine, counterexample generator, code assistant, translation layer và compression engine.

**Search/literature** cung cấp prior work và external evidence.

**Code/proof tools** kiểm tra transformation, simulation, schema, link, formal proof khi có.

Tool use không quyết định truth-value:

\[
ToolUsed\not\Rightarrow Invalid
\]

nhưng tool-induced error hoàn toàn là critique hợp lệ nếu chỉ được lỗi cụ thể.

## Provenance của đóng góp

PCRO phải ghi rõ ai/công cụ làm phần nào thay vì chỉ binary “AI/no AI”. Ví dụ:

- conceptualization: human-primary;
- architecture: human-primary;
- formalization: human+LLM;
- literature retrieval: LLM/search-assisted;
- validation: mixed;
- writing: collaborative;
- final responsibility: human author.

Đây là cách tăng transparency mà không biến tool thành stigma.
