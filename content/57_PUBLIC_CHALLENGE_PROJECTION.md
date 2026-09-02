# 57 — BL∞ Public Challenge Projection

**Object:** `BL-CHALLENGE-PROJECTION`  
**Tên Việt:** Bản Chiếu Thử Thách Công khai BL∞  
**Class:** progressive-disclosure / public research challenge / provenance-preserving redaction policy  
**Status:** `ADOPTED · PUBLIC · OPEN-TO-AUDIT`  
**Origin:** Lâm Kim Bách / Bách Lâm  
**Version:** `1.1`  
**Date:** `2026-09-02`

---

## 0. Mục đích

Một public research object không bắt buộc phải công bố toàn bộ closure, derivation hoặc implementation detail chỉ để được xem là công khai. BL∞ từ phiên bản này cho phép một số **công thức có đòn bẩy cao** được chuyển từ full public form sang **Challenge Projection**.

Challenge Projection không tạo công thức sai và không giả vờ rằng omission là lỗi vô ý. Nó nói rõ rằng public edition đang giữ lại một phần closure và chỉ phát hành đủ cấu kiện để người đọc tự tái dựng, phản biện hoặc chứng minh một phương án độc lập.

```text
Withheld != False
Hint != FullClosure
PublishedProjection != CompleteDerivation
Challenge != Deception
HistoricalRelease != CurrentDisclosureChoice
```

## 1. Ba trạng thái công thức

### OPEN_FORMULA

Công thức đầy đủ được công khai và có thể được dùng trực tiếp.

### CHALLENGE_HINT

Không công khai compact/full closure. Public edition chỉ giữ:

- input/output hoặc biến liên quan;
- invariant bắt buộc;
- direction/relationship;
- counterexample hoặc falsifier;
- điều kiện biên;
- đủ provenance để biết đây là omission có chủ đích.

### FORMULA_WITHHELD

Công thức đầy đủ không nằm trên current public surface. Public text phải nói rõ điều này; không được thay bằng một công thức sai rồi để người đọc tưởng là canonical.

## 2. Challenge contract

Một challenge hợp lệ phải cho phép người đọc phân biệt:

```text
known statement
vs.
hint
vs.
unknown
vs.
withheld closure
```

Không được dùng Challenge Projection để:

- che counterevidence đã biết;
- biến một claim yếu thành claim mạnh;
- làm một công thức sai trông như công thức đúng;
- xóa causal history;
- tuyên bố người khác “sai” chỉ vì họ không đoán được phần đã giữ lại.

## 3. Reconstruction challenge

Người đọc được mời tự dựng candidate closure từ public constraints. Một lời giải mạnh nên:

1. tái tạo được behavior/invariants đã công bố;
2. không mâu thuẫn Reality Veto;
3. giải thích được countercase đã biết;
4. cho prediction/test hoặc derivation rõ;
5. ghi provenance và assumptions;
6. không tự nhận identity với công thức tác giả nếu chưa có bằng chứng.

```text
IndependentReconstruction != AuthorialIdentity
FunctionalEquivalence != HistoricalOrigin
```

## 4. Quan hệ với BL-CONSERVE và BL-OAP

`BL-CONSERVE` giữ lịch sử rằng một object từng có public form nào và vì sao disclosure state đổi. `BL-OAP` vẫn cho phép public critique đối với phần đã phát hành.

```text
CurrentProjection may be reduced
while
CausalHistory remains reconstructable
```

Do Git lưu lịch sử commit, một công thức đã từng được commit công khai trước đây có thể vẫn tồn tại trong historical repository history. Challenge Projection chủ yếu kiểm soát **current/future public release surface**, không giả vờ xóa quá khứ đã công khai.

## 5. Quy tắc triển khai

Khi một công thức được chuyển sang Challenge Projection, source hiện hành dùng marker dạng:

```text
[FORMULA_WITHHELD: <OBJECT-ID>]
```

sau đó là `Public hint` mô tả đủ constraint để việc phản biện còn có nghĩa.

Không có marker nghĩa là không được tự suy rằng một biểu thức bị thiếu là bí mật hay lỗi cố ý.

## 6. Ý nghĩa của thử thách

Mục tiêu không phải khiến người đọc thất bại. Mục tiêu là phân biệt ba năng lực:

- người chỉ sao chép expression;
- người hiểu dependency và invariant;
- người có thể độc lập tái dựng, kiểm chứng và cải tiến.

Một reconstruction tốt có thể trở thành critique, alternate formalization hoặc independent result trong BL-OAP, nhưng vẫn giữ đúng attribution và provenance.

## 7. BL-RECON-PUZZLES — lớp toán đố tái dựng

Challenge Projection có một lớp bài toán người đọc tự giải tại `content/58_RECONSTRUCTION_PUZZLES.md` và public human surface `/research-puzzles.html`.

Mỗi bài gắn với một `FORMULA_WITHHELD` object nhưng **không phải encoded answer key**. Puzzle chỉ cung cấp:

- scenario;
- invariants;
- boundary cases;
- trap/countercase;
- một hint có kiểm soát.

Public repository **không chứa canonical answer key** cho lớp này.

```text
Puzzle != CiphertextOfAnswer
Hint != EncodedFormula
Solve != GuessAuthorText
```

Người giải được phép tạo một formalization tốt hơn expression lịch sử. Đánh giá dựa trên sức mạnh logic, countercase survival và provenance, không dựa trên việc đoán đúng từng ký hiệu tác giả từng dùng.

### Human-only credit là một provenance claim, không phải DRM

Một static public site không có cách đáng tin cậy để chứng minh người đọc không dùng GPT, CAS, theorem prover, code hoặc công cụ ngoài. Vì vậy BL∞ không giả vờ có “AI-proof DRM”. Thay vào đó submission muốn nhận nhãn `INDEPENDENT_HUMAN_RECONSTRUCTION` phải tự khai tool provenance.

```text
UndeclaredToolUse -> provenance failure
DeclaredAIAssistance -> valid assisted submission, not human-only credit
```

### Discovery minimization

Human puzzle surface được thiết kế để:

- không nằm trong sitemap;
- không được gửi IndexNow;
- không được thêm vào `llms.txt` hoặc machine discovery manifest;
- dùng `noindex`, `nofollow`, `noarchive`, `nosnippet` trên trang;
- vẫn thừa nhận rằng bất kỳ nội dung nào thực sự gửi tới browser đều có thể bị người dùng hoặc công cụ đọc/copy.

Do đó lớp bảo vệ thật là **không phát hành full closure/answer key**, còn noindex/obfuscation chỉ là defense-in-depth và friction.
