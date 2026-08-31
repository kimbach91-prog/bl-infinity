# 11 — Lý thuyết phản biện đồng cấp

## BL-LC — Level-Matched Critique Principle

Một critique C muốn refute claim H phải tác động vào ít nhất một biến quyết định truth-status của H.

Ký hiệu:

\[
Critical(H)=\{v_1,\dots,v_n\}
\]

\[
Touched(C,H)=Variables(C)\cap Critical(H)
\]

Một metric định hướng:

\[
LevelMatch(C,H)=\frac{|Touched(C,H)|}{|Critical(H)|}
\]

Metric không phải theorem về chất lượng critique. Một counterexample duy nhất có thể chạm rất ít biến nhưng đủ bác universal claim. Mục đích là ép reviewer khai báo **điểm tấn công**.

## Taxonomy critique

- **R1 Definition conflict:** definition tự mâu thuẫn hoặc dùng không nhất quán.
- **R2 Invalid inference:** conclusion không theo premises.
- **R3 Counterexample:** một instance hợp lệ bác universal claim.
- **R4 Countermodel:** model thỏa premises nhưng không thỏa conclusion.
- **R5 Empirical contradiction:** measurement không phù hợp prediction.
- **R6 Hidden assumption:** assumption quyết định bị giấu.
- **R7 Scope violation:** conclusion vượt phạm vi proof.
- **R8 Reproducibility failure:** không tái tạo được computation/experiment.
- **R9 Prior-art challenge:** tác động novelty/priority, không tự động tác động truth.
- **R10 Formal inconsistency:** axiom/theorem set sinh contradiction không được xử lý.
- **R11 Tool-induced error:** AI/code/calculator tạo lỗi cụ thể có thể truy được.
- **R12 Provenance challenge:** bằng chứng nguồn gốc/timeline không đủ hoặc bị mâu thuẫn.

## Những phản ứng có trọng lượng bằng 0 nếu đứng một mình

- tác giả không có bằng đúng ngành;
- tác giả dùng AI;
- tác giả làm việc một mình;
- tác giả không thuộc viện lớn;
- tác giả viết trên GitHub;
- tác giả nổi tiếng hoặc không nổi tiếng;
- ý tưởng nghe kỳ lạ;
- công kích tính cách không liên quan claim.

Các dữ kiện trên có thể liên quan ở một context cụ thể, nhưng phải chỉ ra causal path tới lỗi của claim.

## Không tạo “đặc quyền phản biện” cho BL∞

Nguyên lý đồng cấp không có nghĩa critique phải dài bằng theory hay người phản biện phải có credential tương đương. Một counterexample 3 dòng có thể đủ. “Đồng cấp” nghĩa là **đúng tầng truth-condition**, không phải ngang địa vị hay số chữ.
