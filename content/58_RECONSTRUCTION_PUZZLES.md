# 58 — BL∞ Reconstruction Puzzles

**Object:** `BL-RECON-PUZZLES`  
**Tên Việt:** Toán đố Tái dựng BL∞  
**Class:** human research challenge / mathematical reconstruction exercise  
**Status:** `PUBLIC CHALLENGE · NO PUBLIC ANSWER KEY`  
**Parent policy:** `BL-CHALLENGE-PROJECTION`  
**Origin:** Lâm Kim Bách / Bách Lâm  
**Version:** `1.0`  
**Date:** `2026-09-02`

---

## 0. Luật chơi

Các bài dưới đây không phải kiểm tra trí nhớ và không yêu cầu đoán đúng nguyên văn một công thức lịch sử. Mục tiêu là xem người giải có thể **tái dựng một formalization đủ mạnh từ invariant, boundary condition và countercase** hay không.

```text
GoodPuzzleSolution
= ExplicitAssumptions
+ ValidDerivation
+ InvariantPreservation
+ CountercaseHandling
+ TestableConsequences
+ Provenance
```

Không có answer key canonical trên public repository.

Một lời giải dùng AI, CAS, theorem prover hoặc solver vẫn có thể hữu ích, nhưng nếu muốn được ghi nhận là **independent human reconstruction**, người giải phải tự khai báo công cụ đã dùng. Không có cơ chế kỹ thuật đáng tin cậy nào trên một static public page để chứng minh một người “không dùng AI”.

---

## P1 — Miền khả đạt biết mất trí nhớ

Liên quan: `BL-A05-DYNAMIC-REACHABILITY`.

Một agent có state `x_t`, repertoire `U_t`, tài nguyên `R_t` và tập quyền `P_t`. Trong ba bước liên tiếp:

- bước 0: có tool `a`, `b`;
- bước 1: có thể chế tạo `c` nếu còn `a` và đủ tài nguyên;
- bước 2: mất `a`, nhưng `c` vẫn tồn tại;
- một target `h` chỉ tạo được khi có `b` và `c` đồng thời.

**Yêu cầu:** đề xuất một recurrence cho reachable region theo thời gian sao cho:

1. không mặc định monotonic;
2. phân biệt tool đang sở hữu với tool có thể chế tạo;
3. xử lý resource/permission loss;
4. giải thích tại sao `h` có thể reachable ở một thời điểm nhưng không reachable ở thời điểm khác.

**Bẫy:** công thức chỉ dùng `U_{t+1}=U_t ∪ NewTools` mà không có loss operator là chưa đủ.

---

## P2 — Năm tấm kính của người quan sát

Liên quan: `BL-A06-OBSERVATION-FILTER-COMPOSITION`.

Một tín hiệu từ thế giới phải đi qua năm loại biến đổi: stability, causal exposure, access, detector và cognition. Ta biết:

- detector không thể nhận thứ chưa từng đến được causal vicinity;
- cognition không thể khôi phục hoàn hảo dữ liệu detector chưa ghi;
- access có thể chặn một tín hiệu dù tín hiệu tồn tại và ổn định;
- hai filter khác loại đôi khi không commute.

**Yêu cầu:** xây một composition hợp lý và nêu rõ điều kiện nào khiến hai ordering khác nhau cho output khác nhau.

**Điểm cộng:** chỉ ra phần nào của ordering là identifiable từ observation và phần nào có thể observationally equivalent.

---

## P3 — Cây cầu không được phép nhảy

Liên quan: `BL-A09-PLENITUDE-BRIDGE`.

Cho một logic `L` và predicate `Cons_L(h)` nói rằng description `h` nhất quán trong `L`.

Ta **không** cho phép suy trực tiếp:

```text
Consistent description -> physically actual object here-and-now
```

**Yêu cầu:** đề xuất **bridge assumption yếu nhất mà bạn dám nhận trách nhiệm** để đi từ consistency tới một dạng realization-domain nào đó. Sau đó:

1. chỉ ra bridge đó mạnh hơn consistency ở điểm nào;
2. nêu một countermodel nếu bỏ bridge;
3. tách `formal realization`, `reachable construction` và `physical actuality`.

**Bẫy:** đổi tên “tưởng tượng được” thành “tồn tại” không phải chứng minh.

---

## P4 — Xưởng công cụ tự sinh

Liên quan: `BL-RCA-RECURSIVE-CAPABILITY-UPDATE`.

Ta có bốn capability ban đầu/tiềm năng:

- `A` có sẵn;
- `B` xây được từ `A`;
- `C` cần `A+B`;
- `D` cần `C` nhưng khi xây `D` thì tiêu hao `B` vĩnh viễn.

**Yêu cầu:** định nghĩa update operator cho repertoire sao cho mô hình phân biệt:

- acquired capability;
- constructible capability;
- consumed capability;
- persistent capability.

Sau đó tính các state khả dĩ sau tối đa bốn bước và chỉ ra vì sao “closure” có thể phụ thuộc path.

---

## P5 — Closure có lịch sử

Liên quan: `BL-RCA-LONG-HORIZON-REACHABLE-CLOSURE`.

Cho directed state graph có cạnh chỉ xuất hiện khi một capability tương ứng đang tồn tại. Một số capability được tạo ra bởi việc đi qua cạnh trước đó; một số khác hết hạn sau `k` bước.

**Yêu cầu:** formalize một long-horizon reachable set **có history dependence**.

Một lời giải mạnh phải trả lời:

1. state `s` có thể reachable theo path 1 nhưng không theo path 2 không;
2. union của các one-step reachable set có đủ không;
3. cần lift state thành `(world_state, capability_state, history_summary)` ở mức nào.

---

## P6 — Xác suất bằng không không phải rất nhỏ

Liên quan: `BL-RCA-POSITIVE-ACCESSIBILITY-LIMIT`.

Mỗi trial độc lập có xác suất `p` hit target. Không được giả định trước `p > 0`.

**Yêu cầu:** tự dựng biểu thức cho xác suất chưa từng hit sau `n` trial và phân tích giới hạn khi `n -> infinity` cho ít nhất ba trường hợp:

- `p = 0`;
- `0 < p < 1`;
- `p` thay đổi theo thời gian và có thể tiến về 0.

**Điểm cộng:** nêu điều kiện đủ trên chuỗi `p_t` để hit xảy ra với xác suất 1, thay vì dùng khẩu hiệu “vô hạn thời gian thì mọi thứ xảy ra”.

---

## P7 — Trí tuệ sửa nhanh nhưng quên sạch

Liên quan: `OPT-REC-EPISTEMIC-QUALITY`.

Ba biến chuẩn hóa trong `[0,1]`:

- `e`: error-detection quality;
- `r`: revision quality;
- `u`: useful-retention quality.

Ta muốn một quality functional `Q(e,r,u)` thỏa tối thiểu:

1. tăng theo từng biến khi hai biến còn lại cố định;
2. hệ có `u=0` không được xếp ngang hệ giữ được tri thức hữu ích;
3. không được để một biến cực lớn che hoàn toàn một biến gần 0;
4. có cách mở rộng để thêm chi phí/latency mà không đổi ý nghĩa ba biến lõi.

**Yêu cầu:** đề xuất ít nhất hai candidate functional, so sánh ưu/nhược và đưa counterexample làm một candidate thất bại.

**Bẫy:** weighted sum đơn giản có thể cho một thành phần bù vô hạn cho thành phần gần bằng 0.

---

## P8 — Phiên bản mới không được giết lịch sử

Liên quan: `OPT-REC-VERSION-UPDATE-OPERATOR`.

Cho state nghiên cứu `B_n`, evidence mới `E_n`, critique `C_n`, tool/theory mới `T_n`, cùng dependency graph `G_n`.

Một critique hợp lệ làm claim `c` bị reject; ba claim khác phụ thuộc trực tiếp/gián tiếp vào `c`, nhưng một claim thứ tư chỉ cùng lineage chứ không phụ thuộc logic.

**Yêu cầu:** thiết kế update operator tạo `B_{n+1}` sao cho:

- propagation chỉ đi qua dependency thích hợp;
- negative knowledge được giữ;
- lineage không bị nhầm với dependency;
- superseded state vẫn reconstructable;
- không silent rewrite provenance.

**Điểm cộng:** mô tả minimal causal delta cần ghi để auditor tái dựng vì sao mỗi claim đổi status.

---

## Cách nộp một lời giải đáng xem

Một submission tốt nên có:

```text
Puzzle ID
Assumptions
Definitions
Candidate formula / operator
Derivation
Counterexamples tested
Boundary cases
What remains UNKNOWN
Tools used (human-only / AI-assisted / CAS / prover / code)
```

Không chấm theo việc “đoán trúng bí mật”. Chấm theo **độ mạnh của formalization, khả năng sống sót qua countercase và tính minh bạch provenance**.

> Người giải được quyền vượt qua lời giải mà tác giả từng dùng. Nếu một reconstruction tốt hơn, nó nên được đánh giá như một đóng góp mới chứ không bị ép quay về một expression lịch sử.
