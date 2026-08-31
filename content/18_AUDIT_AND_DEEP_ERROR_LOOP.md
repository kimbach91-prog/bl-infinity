# 18 — Phát kiến quy trình: Audit lỗi sâu sau đóng gói

Một discovery workflow thông thường thường làm:

\[
Draft\to Review\to Publish
\]

BLOK đề xuất pipeline hai pha mạnh hơn:

\[
Discovery\to Packaging\to StructuralDefense\to Publication\to DeepAudit\to Revision
\]

Lý do: trước khi audit sâu, claim phải được **đóng gói đủ rõ để biết ta đang audit cái gì**. Một tư tưởng còn phân tán trong chat hoặc trí nhớ rất khó bị phản biện chính xác.

## Phase A — Packaging audit

Kiểm tra:

- claim có ID chưa;
- type đúng chưa;
- axiom/theorem/conjecture có bị lẫn không;
- dependency có đầy đủ không;
- source/provenance có rõ không;
- scope có khai báo không;
- falsifier/attack surface có tồn tại không;
- canonical wording có ổn định không.

## Phase B — Deep adversarial audit

Sau khi object ổn định, chạy từng lớp:

1. semantic consistency;
2. formal logic;
3. countermodel generation;
4. mathematical correctness;
5. modal/ontological critique;
6. empirical interface;
7. prior-art identity test;
8. scope creep test;
9. circularity/self-sealing test;
10. AI hallucination/source test;
11. hostile reviewer;
12. reconstruction by an AI with no prior conversation context.

## Audit recursion

\[
Audit_n\to Findings_n\to Patch_n\to Audit_{n+1}
\]

Một issue được đóng chỉ khi response chỉ ra evidence hoặc patch tương ứng. Việc một objection bị “trả lời” bằng văn phong không đủ để chuyển status sang resolved.

Đây là **BL-DAL — Deep Audit Loop**, một process technology nằm trong BL-RAP/BL-AEGIS.
