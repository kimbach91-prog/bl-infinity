# 25 — Mô hình quyền phát biểu học thuật mở

BL∞/OODP không đặt mục tiêu thay mọi đại học, tạp chí hay phòng thí nghiệm. Nó nhắm tới một bottleneck khác: **quyền biến một ý tưởng thành một object nghiêm túc có provenance, machine-readable structure và bề mặt phản biện** không nên phụ thuộc hoàn toàn vào institutional membership.

## 1. Hai quyền phải tách

\[
RightToPublish\neq RightToBeBelieved
\]

Một người có quyền công bố research object. Người đọc không có nghĩa vụ chấp nhận nó.

Trọng lượng phải được xây bằng:

\[
EpistemicWeight=f(clarity,derivation,evidence,reproducibility,critiqueSurvival)
\]

## 2. Hệ cũ tối ưu cái gì?

Tạp chí/peer review truyền thống giải quyết nhiều vấn đề thật:

- scarcity của page/attention;
- minimum filtering;
- attribution;
- editorial quality;
- archiving;
- community signaling.

Nhưng khi storage/distribution gần như miễn phí và AI giảm cost formalization, một số scarcity assumptions thay đổi. Vấn đề chuyển từ “ai được xuất bản” sang “cái gì đáng attention/verification”.

## 3. Preservation queue và verification queue

OODP đề xuất hai queue:

### Preservation queue
Entry cost thấp; mọi research object đạt schema/provenance tối thiểu được archive.

### Verification queue
Tài nguyên đắt hơn được phân bổ theo expected information/impact value.

Điều này chống hai lỗi:

- **false rejection:** idea tiềm năng chết trước khi được nhìn;
- **attention collapse:** mọi idea được coi ngang nhau.

## 4. Blind epistemic pass

Một review mode có thể tạm ẩn:

- chức danh;
- follower;
- viện;
- quốc gia;
- wealth/status;

để reviewer đầu tiên thấy claim graph trước. Sau đó metadata được mở khi nó thật sự relevant, ví dụ conflict of interest, domain competence, data custody.

## 5. Credential không bị xóa

OODP không nói credential vô nghĩa. Nó nói credential là **evidence about expected competence**, không phải evidence trực tiếp cho truth của từng claim.

Bayesian prior có thể dùng:

\[
P(error|training)
\]

nhưng khi proof/evidence cụ thể xuất hiện, posterior phải cập nhật theo nội dung.

## 6. Reviewer accountability

Review cũng là scholarly object. Một critique có ID, provenance và outcome. Theo thời gian có thể đo:

- objections upheld;
- false alarms;
- useful corrections;
- counterexamples discovered;
- replication success.

Không biến metric thành điểm quyền lực tuyệt đối; dùng nó như history để calibrate trust.

## 7. Credit graph

Nếu critic C sửa claim P của author A:

\[
A\xrightarrow{authored}P
\]

\[
C\xrightarrow{identified\ flaw}R
\]

\[
R\xrightarrow{caused\ revision}P'
\]

Credit của C được giữ thay vì theory chỉ mang tên origin author.

## 8. Chống độc quyền mới

Một hệ “giải phóng học thuật” có thể tự biến thành gatekeeper mới. Guardrails:

- protocol open;
- schema forkable;
- public critique logs;
- no secret scoring formula for public epistemic weight;
- multiple independent indexes allowed;
- signed canonical lineage để fork không xóa nguồn;
- no requirement to agree with BL∞ to use BLOK.

## 9. Tiêu chuẩn thành công

OODP thành công không phải khi “người nghiệp dư thắng giáo sư”. Nó thành công nếu:

- một idea chất lượng từ ngoài institution được preserve nhanh hơn;
- low-quality idea bị diagnosis cụ thể hơn;
- prior-art disputes rõ hơn;
- independent derivations được ghi nhận;
- critique useful nhận credit;
- cost từ idea tới auditable research object giảm mạnh.
