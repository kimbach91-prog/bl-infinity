# VTTN Specification v0.1

## 0. Phạm vi

Tài liệu này định nghĩa phần công khai an toàn của Việt Toán–Triết Ngữ (VTTN): cú pháp lõi, hệ kiểu, modality, concept registry, canonical IR và quy tắc tương thích. Nó không chứa ontology nội bộ, routing policy hay protected semantics của DEUS.

## 1. Đơn vị cơ bản

### 1.1 Khái niệm

Mọi khái niệm chuẩn có một `concept_id` bất biến theo nghĩa, ví dụ:

```text
KN.LOGIC.DUNG.001
KN.LOGIC.SAI.001
KN.EPISTEMIC.CHUA_BIET.001
KN.CAUSAL.NGUYEN_NHAN.001
KN.CAUSAL.HE_QUA.001
KN.NORM.QUYEN.001
KN.NORM.CAM.001
KN.EVIDENCE.NGUON.001
```

Tên hiển thị có thể đổi theo thời đại/ngữ cảnh nhưng `concept_id` không đổi nếu nghĩa không đổi.

### 1.2 Từ bề mặt

Một từ bề mặt có metadata tối thiểu:

```text
surface
register = hiện_đại | hán_việt | thuần_việt | lịch_sử
concept_id
provenance
valid_from
valid_to?
status = chuẩn | biến_thể | lịch_sử | thử_nghiệm
```

## 2. Hệ kiểu

VTTN dùng hệ kiểu tường minh, có thể mở rộng:

```text
ĐúngSai          = đúng | sai
TriThức          = đã_biết | chưa_biết | bất_định
Số               = số_nguyên | số_thực | số_hữu_tỉ | ...
Chuỗi
ThờiĐiểm
KhoảngThờiGian
TácNhân
TàiNguyên
BằngChứng
Nguồn
Quyền
NghĩaVụ
MệnhĐề<T>
Tập<T>
Dãy<T>
QuanHệ<A,B>
Hàm<A -> B>
XácSuất<T>
ĐộTinCậy<T>
```

Một biểu thức không vượt qua type-check thì không được vào canonical IR.

## 3. Modality

VTTN phân biệt các loại phát biểu để tránh trộn lẫn dữ kiện và suy đoán:

```text
thực_tại(P)      # observed/reality-bound
quan_sát(P)      # directly observed
suy_luận(P)      # inferred
ước_đoán(P)      # conjectured
có_thể(P)        # possible
phải(P)          # necessary/obligatory depending on namespace
được_phép(P)     # permitted
cấm(P)           # prohibited
biết(A,P)        # agent A knows P
độ_tin_cậy(P,r)  # confidence annotation
```

Parser bắt buộc namespace khi một từ có nhiều nghĩa logic, ví dụ `phải` có thể là `modal.tất_yếu` hoặc `norm.nghĩa_vụ`.

## 4. Cú pháp lõi

### 4.1 Định nghĩa

```vttn
định_nghĩa TamGiác = Hình có 3 cạnh.
```

### 4.2 Mệnh đề

```vttn
mệnh_đề P(x: Số) : x > 0.
```

### 4.3 Lượng từ

```vttn
mọi x ∈ A : P(x).
tồn_tại x ∈ A : P(x).
```

### 4.4 Điều kiện

```vttn
nếu P thì Q.
nếu P và Q thì R.
nếu P thì Q ngược_lại R.
```

### 4.5 Chứng minh và nguồn

```vttn
chứng_minh MệnhĐề_A bằng {
  bước 1: ...
  bước 2: ...
}.

nguồn S = tài_liệu("...") với độ_tin_cậy 0.93.
```

### 4.6 Quyền và nghĩa vụ

```vttn
quyền Dùng(node, gpu) khi grant.hiệu_lực == đúng.
cấm Dùng(node, gpu) khi grant.hiệu_lực != đúng.
```

## 5. Quy tắc không nhập nhằng

1. Từ khóa chuẩn không phụ thuộc dấu câu tự nhiên để xác định scope.
2. Tên khái niệm máy dùng `_` hoặc namespace; văn bản diễn giải có thể dùng dấu cách bình thường.
3. Đồng âm/đa nghĩa phải resolve sang `concept_id` trước canonicalization.
4. Parser không được tự đoán một nghĩa bảo mật-nhạy cảm khi có nhiều mapping hợp lệ.
5. Từ lịch sử không được coi là chuẩn hiện đại nếu thiếu provenance.

## 6. Canonical VTTN-IR

VTTN-IR là cây/đồ thị semantic có thứ tự canonical. Ví dụ:

```json
{
  "v":"vttn-ir/0.1",
  "kind":"if",
  "condition":{
    "kind":"call",
    "concept":"KN.AUTH.QUYEN_DUNG.001",
    "args":["node","gpu"]
  },
  "then":{
    "kind":"permit",
    "concept":"KN.EXEC.THUC_THI.001"
  },
  "else":{
    "kind":"prohibit",
    "concept":"KN.EXEC.THUC_THI.001"
  }
}
```

IR canonical phải thỏa:

```text
Unicode normalized
keys sorted by canonical order
concept IDs resolved
numeric encoding deterministic
type annotations explicit
source text optional
provenance references content-addressed where possible
```

## 7. Khả năng biên dịch

Một compiler VTTN chuẩn có bốn chế độ:

```text
parse      source -> AST
resolve    AST -> typed semantic AST
canon      typed AST -> VTTN-IR
render     VTTN-IR -> Vietnamese surface
```

Hai implementation độc lập phải tạo cùng VTTN-IR cho cùng một chương trình hợp lệ.

## 8. Phiên bản và tương thích

- `v0.x`: thử nghiệm, có thể phá tương thích.
- `v1.x`: grammar core ổn định.
- Concept package version độc lập với compiler version.
- Một `concept_id` đã public không được đổi nghĩa; nếu nghĩa đổi phải cấp ID mới.

## 9. Lớp lịch sử tiếng Việt

VTTN không coi “cổ” là mỹ thuật. Mọi mục lịch sử phải có:

```text
nguồn văn bản / từ điển / nghiên cứu
niên đại hoặc khoảng niên đại
cách đọc/phục dựng nếu có
nghĩa trong ngữ cảnh gốc
mức chắc chắn
liên hệ với khái niệm hiện đại
```

Nếu thiếu dữ liệu, trạng thái phải là `chưa_xác_minh`, không được tự tạo nguồn gốc.

## 10. Profile DEUS

Public VTTN chỉ định grammar và semantic machinery chung. DEUS có thể dùng private profile gồm ontology, capability classes, routing semantics và model-specific optimization, nhưng private profile phải biên dịch xuống cùng cơ chế IR/type/provenance để giữ khả năng audit.

Nguyên tắc bảo mật:

```text
public grammar != public ontology
public concept mechanism != public private-concept dictionary
readable source != exposed protected reasoning
```

## 11. Mục tiêu kiểm thử v0.1

- round-trip source -> IR -> source;
- deterministic canonicalization;
- ambiguity rejection;
- Unicode normalization tests;
- Hán–Việt/thuần Việt alias equivalence tests;
- provenance-required historical lexicon tests;
- type errors fail closed;
- security-sensitive concept resolution fails closed on ambiguity.
