# 36 — BL-ICO: Indexable Claim Object

Origin Build v0.1.0 có một hạn chế kỹ thuật: toàn bộ claim được hiển thị trên một `claims.html`. Điều này đủ để đọc nhưng chưa tối ưu cho indexing, citation, comment và audit ở cấp mệnh đề.

BL-ICO sửa vấn đề này.

## 36.1. Định nghĩa

**BL-ICO — Indexable Claim Object** là một claim có:

1. Claim ID ổn định;
2. canonical URL riêng;
3. canonical statement;
4. type/status/scope;
5. dependency;
6. attack surface/falsifier;
7. parent theory/assets;
8. machine-readable representation;
9. comment/discussion surface riêng theo pathname;
10. inclusion trong sitemap và claim graph.

Mapping:

\[
Fragment\to ClaimURL\to ClaimID\to Theory\to Author\to Provenance
\]

## 36.2. Giá trị kỹ thuật

Một người hoặc crawler có thể link trực tiếp tới `BL-NCI` thay vì trỏ vào một trang dài rồi mô tả “đoạn khoảng giữa”. Điều này giảm ambiguity và tăng khả năng:

- citation;
- deep-link;
- search indexing;
- critique targeting;
- version comparison;
- AI reconstruction.

## 36.3. Không đồng nhất index với xác nhận

\[
Indexed(x)\not\Rightarrow Valid(x)
\]

BL-ICO chỉ làm claim addressable và auditable. Truth-status vẫn thuộc logic/evidence/audit.

## 36.4. Technical implementation

Build v0.2 sinh URL dạng:

`/claims/<claim-id>/`

và asset URL dạng:

`/assets/<asset-code>/`

Mỗi URL có canonical tag, metadata và JSON-LD. Sitemap chứa các URL này. Đây là lớp kỹ thuật phục vụ BL-IDX và BL-AEGIS.
