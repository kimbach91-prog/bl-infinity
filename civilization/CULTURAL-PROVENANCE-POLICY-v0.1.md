# Cultural Provenance Policy v0.1

Mục tiêu: bảo tồn và biểu diễn tri thức/ngôn ngữ/văn hóa Việt Nam theo cách hữu ích cho con người và máy nhưng không làm phẳng khác biệt lịch sử, vùng miền hay trường phái.

## 1. Bốn lớp bắt buộc

Mỗi mục văn hóa phải phân loại ít nhất một trong bốn lớp:

- `ARTIFACT`: vật/chữ/âm thanh/hình ảnh/tư liệu có thể chỉ đến nguồn cụ thể.
- `HISTORICAL_CLAIM`: mệnh đề về quá khứ, cần nguồn và mức tranh luận.
- `INTERPRETATION`: cách hiểu của tác giả/trường phái/cộng đồng/thời đại.
- `CREATIVE_DERIVATIVE`: sáng tạo mới dựa trên di sản.

Không được nhập bốn lớp này thành một fact duy nhất.

## 2. Từ Việt cổ và Hán–Việt

Một dạng từ lịch sử chỉ được đánh dấu `reviewed/canonical` khi có attestation/provenance đủ rõ. Trường bắt buộc nên gồm:

```text
form
reading / pronunciation (nếu có nguồn)
script / orthography
period
region/community
meaning-in-context
sourceRef
editorial interpretation
confidence/status
```

Thiếu nguồn: giữ `draft` hoặc `UNSOURCED`, không dựng từ nguyên nghe hợp lý rồi gắn như lịch sử.

## 3. Phương ngữ và đa dạng vùng

Không dùng một biến thể hiện đại làm “chuẩn bản thể” để hạ các biến thể khác thành sai. Canonical concept có thể có nhiều alias theo region/community; chuẩn chính tả hành chính chỉ là một register.

## 4. Truyền khẩu

Nguồn truyền khẩu được lưu như `oral` provenance với người kể/người ghi/địa điểm/thời gian/quyền sử dụng khi có. Không tự hạ giá trị vì không phải văn bản, nhưng cũng không tự nâng thành historical fact nếu chưa có corroboration.

## 5. Văn bản dịch và phục dựng

- scan/photo != transcription
- transcription != normalized text
- normalized text != translation
- translation != interpretation
- reconstruction != original

Mỗi lớp là artifact mới có `derivedFrom` riêng.

## 6. Quyền và cộng đồng

Có dữ liệu công khai về mặt kỹ thuật nhưng không nhất thiết phù hợp để tái sử dụng vô hạn. Record nên lưu license, quyền, hạn chế cộng đồng và lý do hạn chế khi áp dụng. PRIVATE/RESTRICTED không được mở chỉ vì crawler có thể truy cập nguồn.

## 7. AI-generated material

Nội dung AI suy ra, phục dựng, phiên âm hoặc giải thích phải ghi `computed`/`editorial` provenance và model/tool lineage khi có thể. AI output không được dùng làm nguồn sơ cấp cho chính claim mà nó vừa sinh.

## 8. Tranh luận lịch sử

Nếu có nhiều diễn giải uy tín:

```text
claim A -> evidence set A
claim B -> evidence set B
relationship -> contested
```

Không ép hệ chọn một narrative duy nhất chỉ để giảm độ phức tạp.

## 9. Public heritage vs protected core

Public heritage corpus có thể chứa từ điển, văn bản, metadata, annotation, các mapping chuẩn quốc tế và công cụ đọc/kiểm chứng. Nó không bao gồm DEUS private prompt, raw reasoning, private topology, secret routing policy, proprietary eval/failure corpora hoặc hidden compiler heuristics.

## 10. Tiêu chuẩn chất lượng

Một record cultural PUBLIC/COMMON chỉ được coi là production-ready khi:

- provenance parse được;
- disclosure hợp lệ;
- source/rights không mâu thuẫn hiển nhiên;
- lớp artifact/claim/interpretation/derivative rõ;
- concept IDs có thể resolve;
- hash hợp lệ;
- nếu contested thì counter-position không bị xóa khỏi ledger.
