# 56 — Hệ Bảo Toàn BL∞ và Công nghệ Xuất bản Tự do Học thuật

**Object:** `BL-CONSERVE`  
**Tên Việt:** Hệ Bảo Toàn BL∞  
**English:** BL∞ Conservation System  
**Class:** cross-system preservation architecture / integration view / publication technology  
**Parent integration:** `BL-INF-UNIFY`  
**Status:** `ADOPTED-AS-CROSS-SYSTEM-CONSERVATION-LAYER · OPEN-TO-AUDIT`  
**Origin:** Lâm Kim Bách / Bách Lâm  
**Version:** `0.1`  

---

## 0. Vì sao cần một Hệ Bảo Toàn

BL∞ đã có nhiều học thuyết, proposition, doctrine, protocol, machine object, public page và narrative object. Vấn đề tiếp theo không phải tạo thêm một “Meta-OS” đứng trên tất cả. Vấn đề là bảo đảm khi toàn hệ tiếp tục lớn lên, việc nối các cấu kiện **không xóa identity, provenance, contradiction, trạng thái bằng chứng, lịch sử sửa đổi, UNKNOWN hoặc quyền bị thực tại phủ quyết** của từng cấu kiện.

Hệ Bảo Toàn vì vậy là một **cross-system layer**, không phải truth engine mới và không phải runtime router bí mật.

```text
Conservation != Freezing
Unification != IdentityCollapse
Preservation != Endorsement
Publication != Validation
Indexing != Truth
Revision != Historical Erasure
```

Mục tiêu của `BL-CONSERVE` là làm cho một object có thể tiến hóa mạnh mà vẫn trả lời được:

- nó là gì;
- đến từ đâu;
- đang ở trạng thái nào;
- phụ thuộc vào những gì;
- từng bị phản biện ra sao;
- bằng chứng nào đã làm nó đổi trạng thái;
- phiên bản nào đang được ưu tiên;
- phiên bản nào đã bị supersede;
- cái gì vẫn chưa biết;
- phần nào được công khai, phần nào chỉ là projection;
- và khi một lý thuyết nối với lý thuyết khác, quan hệ đó là loại quan hệ gì.

---

## 1. Conservation Vector

Với một public research object `x`, trạng thái bảo toàn tối thiểu có thể mô hình hóa bằng:

```text
C(x,t) = <
  UID,
  CanonicalName,
  Class,
  ClaimOrContent,
  Scope,
  EpistemicStatus,
  EvidencePlus,
  EvidenceMinus,
  Dependencies,
  TypedRelations,
  Provenance,
  Version,
  CausalHistory,
  Supersession,
  DisclosureClass,
  RealityAnchors,
  OpenUnknowns
>
```

Một update hợp lệ không cần giữ nguyên mọi giá trị, nhưng phải giữ được **đường tái dựng** từ trạng thái cũ sang trạng thái mới:

```text
Update(x,t -> t+1)
=> Preserve(IdentityHistory)
 + Record(Delta)
 + Record(Reason)
 + Record(ProcessOrActor)
 + Record(SupersededState)
```

Nếu một thay đổi lớn xảy ra mà không thể trả lời “đổi cái gì, vì sao, khi nào, bởi process nào, thay cho cái gì”, đó là conservation failure.

---

## 2. Bảy bất biến bảo toàn

### C-1 — Reality authority được bảo toàn

```text
REALITY > Model > Reputation
```

`BL-CONSERVE` không được biến việc “đã công bố” thành lá chắn chống Reality Veto.

### C-2 — Identity được bảo toàn qua hợp nhất

```text
RelatedTo != SameAs
Lineage != Dependency
Formalizes != Originates
Implements != Governs
```

Một supergraph tốt làm quan hệ rõ hơn; nó không nghiền mọi node thành một node duy nhất.

### C-3 — Negative knowledge được bảo toàn

Một falsified path, failed experiment, rejected interpretation hoặc critique có giá trị không được xóa chỉ vì phiên bản mới tốt hơn. Thất bại có thể là dữ liệu giúp tương lai không trả lại đúng cái giá cũ.

### C-4 — UNKNOWN được bảo toàn

Khoảng chưa biết không được tự động điền bằng câu chuyện nghe hợp lý. Nếu ontology hiện hành chưa đủ, trạng thái `UNKNOWN`, `OPAQUE_UNKNOWN` hoặc mixed/contested được phép tồn tại.

### C-5 — Quyền được đề xuất không bị đồng nhất với quyền được tin

```text
RightToPropose != RightToBeBelieved
RightToValidate != RightToExecute
```

Dân chủ Học thuật mở cửa vào quy trình; evidence, reproducibility, adversarial survival và Reality Veto quyết định epistemic weight.

### C-6 — Public verifiability được bảo toàn mà không ép full disclosure

```text
PublicVerifiability != FullRuntimeDisclosure
```

BL-CPR tiếp tục giữ ranh giới giữa public verification surface và các phần không cần công khai để người ngoài đánh giá claim công khai.

### C-7 — Sửa phải tạo causal delta

```text
Version(t+1) = Version(t) + AuditableDelta
```

Đổi số version mà không tạo delta có nghĩa là release noise. Tạo delta mà không version/provenance là history loss.

---

## 3. Toàn hệ được nối thành một vòng bảo toàn

`BL-CONSERVE` không thay thế `BL-INF-UNIFY`; nó đọc đại hệ như một chuỗi những phép biến đổi phải giữ được thông tin thiết yếu.

```text
REALITY
  ↓
BL∞ / BL-OEPS
  ↓ possibility, anomaly, unknown, representation
BLEE + ACADEMIC DEMOCRACY
  ↓ open epistemic entry
BL-HRD
  ↓ hypothesis object
BL-ADN + BL-LOG + BL-CHRONO
  ↓ identity + genealogy + causal history
BL-PCRO + BL-OODP + BLOK
  ↓ preserve-before-validation + package + index
BL-NOVO
  ↓ novelty / prior-art discipline
BL-REV + BL-AEGIS
  ↓ adversarial pressure
RVT / RVP / RVTP / RVL
  ↓ reality-facing correction
BL-SFRET
  ↓ future necessary conditions
OPT-HKRP
  ↓ minimal sufficient resource coalition
OHAS
  ↓ authorized / bounded execution
KAT
  ↓ useful knowledge -> capability
BL-PIRAL + SRS
  ↓ publish -> reaction -> critique -> patch
BL-CPR
  ↓ disclosure boundary
NEW CAPABILITY / NEW EVIDENCE / NEW UNKNOWN
  ↺ back into BL∞
```

### Conservation condition của vòng

Mỗi chuyển tiếp phải cố giữ tối thiểu:

```text
Identity + Provenance + Scope + Status + History + OpenUnknowns
```

Một hệ nhanh hơn nhưng làm mất các trường này có thể tăng output trong ngắn hạn đồng thời tạo **epistemic debt** dài hạn.

---

## 4. Bảo toàn không có nghĩa mọi thứ đều ngang hàng

Hệ thống bảo tồn cả hypothesis yếu và theory mạnh vì cả hai có thể đáng lưu, nhưng **không cấp cùng epistemic weight**.

Một state model gợi ý:

```text
RAW
-> PRESERVED
-> PUBLISHED_UNVERIFIED
-> UNDER_REVIEW
-> SUPPORTED | CONTESTED | NARROWED
-> REVISED | REPLICATED | RETRACTED
```

State có thể rẽ nhánh; không bắt buộc đi một chiều. Một object từng `SUPPORTED` có thể về `CONTESTED` khi evidence mới xuất hiện. Một object `RETRACTED` vẫn được giữ trong causal history.

---

## 5. Công nghệ Xuất bản Tự do Học thuật — BL-OAP

**Working object:** `BL-OAP` — Bach Lam Open Academic Publishing Technology.

“Xuất bản tự do” ở đây không có nghĩa mọi nội dung tự động đúng, cũng không có nghĩa mọi hạ tầng ngoài đời không có chi phí. Nó có nghĩa **không dùng học vị, tổ chức, danh tiếng hay follower count làm điều kiện bắt buộc để một epistemic object đủ cấu trúc được bảo tồn và đi vào bề mặt kiểm tra công khai**.

### 5.1. Pipeline tối thiểu

```text
Author / Independent Scholar / Team / AI-assisted process
-> Create atomic research object
-> Assign persistent ID + canonical statement + scope
-> Attach provenance + dependencies + falsifier
-> Preservation Queue
-> Public publication surface
-> Search/index/machine discovery
-> Public critique
-> Verification Queue
-> Evidence/status update
-> Version / Supersession
-> Re-publication
-> Reusable knowledge object
```

### 5.2. Tách hai queue

**Preservation Queue** hỏi:

- object có định danh được không;
- có provenance tối thiểu không;
- có scope không;
- có bề mặt tấn công/điều kiện sửa không;
- có vi phạm disclosure/safety boundary không.

Nó **không hỏi object đã đúng chưa**.

**Verification Queue** hỏi:

- loại claim này cần proof, measurement, replication hay consistency test nào;
- prior art nào liên quan;
- counterevidence nào tồn tại;
- reviewer/critic nào có competence phù hợp;
- confidence/state nên cập nhật ra sao.

```text
Preserved != Verified
Published != Verified
Popular != Verified
```

### 5.3. Object-first review

Đơn vị được phản biện là object, không phải địa vị người nói.

Một publication có thể được atomize thành:

```text
Publication
-> Claim IDs
-> Definitions
-> Dependencies
-> Evidence anchors
-> Falsifiers
-> Critiques
-> Versions
```

Nhờ vậy một người ngoài viện nghiên cứu vẫn có thể đưa một claim vào hệ; đồng thời một giáo sư, công ty hoặc AI cũng không được miễn phản biện chỉ vì status.

### 5.4. AI trong BL-OAP

AI có thể:

- formalize;
- dịch;
- tìm dependency;
- dựng prior-art map;
- tạo counterexample;
- kiểm tra consistency;
- đóng gói machine-readable object;
- route critique.

Nhưng:

```text
AIFormalization != Evidence
AIGeneration != OriginByDefault
AIConfidence != Reality
```

Authorship/origin/provenance phải được ghi đúng vai trò.

### 5.5. Publication transport có thể thay thế

GitHub Pages, static HTML, JSON/JSON-LD, RSS, sitemap và crawler interfaces là **current public transport**, không phải bản chất của học thuyết.

```text
BL-OAP != GitHub
BL-OAP != OnePlatform
```

Nếu một platform biến mất, object hợp lệ vẫn phải có khả năng migrate với ID map, content hash, lineage và supersession history.

---

## 6. Bảo toàn giữa văn học và nghiên cứu

BL∞ hiện có cả research surface và serialized-fiction surface. Hai miền được nối nhưng không được trộn truth-status.

```text
FictionalEvent != ScientificClaim
RealWorldAnchor != AutobiographicalProof
NarrativeMotif != EmpiricalEvidence
ResearchTheory != FutureStorySpoiler
```

Chương 1 của **Bách Lâm · Lần Hồi Quy Thứ Một Triệu** từ phiên bản kế tiếp dùng trạng thái `HALF-CANON`.

### HALF-CANON không phải “50% xác suất đúng”

Nó là một continuity state gồm ba lớp:

```text
HALF_CANON = LockedCore + RealityAnchors + OpenGaps
```

- **Locked Core:** sự kiện lõi đã công bố được giữ làm dependency cho các chương sau, trừ correction có provenance.
- **Reality Anchors:** bối cảnh lịch sử–xã hội thật được nguồn hóa để thế giới truyện có trọng lượng và không tự bịa lịch sử.
- **Open Gaps:** cơ chế sâu, chronology chưa khóa, future canon và các UNKNOWN không bị ép đóng chỉ để làm truyện có vẻ “giải thích hết”.

Chi tiết texture có thể được nâng cấp nếu không phá dependency. Thay đổi lớn phải explicit supersession/correction.

---

## 7. Reality Anchor Contract cho world build

Một world build dùng thế giới thật cần phân biệt ít nhất bốn loại statement:

```text
R1 = source-backed real historical/social anchor
R2 = contextual cultural pattern with variation explicitly preserved
F1 = fictional scene compatible with known reality
U1 = unknown / intentionally unresolved story mechanism
```

Không được biến `R2` thành “bản chất bất biến của một dân tộc”. Văn hóa, ngôn ngữ, hành vi và thói quen là phân bố có vùng miền, thế hệ, giai tầng, gia đình và thời gian.

Ví dụ với Việt Nam đầu thế kỷ XXI, Chương 1 có thể dùng những neo như:

- Đổi Mới từ 1986 và biến đổi kinh tế–xã hội nhanh;
- kết nối Internet toàn cầu từ 19/11/1997;
- cải cách chương trình/phương pháp giáo dục đầu những năm 2000;
- hội nhập WTO từ 11/01/2007;
- hệ xưng hô dựa mạnh vào kin terms như anh/chị/em/cô/chú/bác, phản ánh tuổi, thế hệ và quan hệ xã hội;
- Tết như một không gian đoàn tụ, ký ức gia đình và nghi thức xã hội;
- đô thị hóa, di chuyển, xe máy, hạ tầng và đời sống gia đình thay đổi nhanh.

Các neo này làm thế giới sống hơn nhưng **không tự chứng minh bất kỳ chi tiết tiểu sử nào của nhân vật Bách Lâm**.

---

## 8. Conservation Matrix cho toàn website

| Surface | Bảo toàn cái gì | Không được suy thành |
|---|---|---|
| `theory.html` | toàn corpus học thuyết công khai | mọi nội dung đều cùng truth-status |
| `claims.html` | claim identity + scope + falsifier | registry entry = truth |
| `assets.html` | named constituent + relation | naming = historical priority |
| `provenance.html` | origin/formalization/history | relation = authorship |
| `critique.html` | counterexample/adverse evidence | critique count = truth vote |
| `machine.html` | machine-readable public contracts | public graph = private runtime |
| Academic Democracy | open scholarly entry | equal epistemic weight |
| BL-OAP | free/open publication pipeline | publication = validation |
| Novel / World | continuity + reality anchors | fiction = science/autobiography |
| BL-CPR | disclosure boundary | secrecy = evidence |

---

## 9. Canonical preservation rules cho các học thuyết đã công bố

1. Mỗi object giữ ID/canonical name riêng.
2. Quan hệ mới phải typed; không dùng “liên quan” khi có thể nói rõ `FORMALIZES`, `DEPENDS_ON`, `CONSTRAINS`, `IMPLEMENTS`, `FEEDS`, `SUPERSEDES`, `CRITIQUES` hoặc loại khác.
3. Không silent retcon.
4. Không xóa negative evidence khỏi public history chỉ vì bất tiện.
5. Không nâng một working formalization thành định luật tự nhiên nếu chưa có external validation phù hợp.
6. Không dùng popularity, SEO, citation count hoặc AI agreement làm truth authority.
7. Không buộc Unknown thành False.
8. Không dùng open ontology để miễn nhiễm một lỗi logic cục bộ.
9. Không dùng conservation để đóng băng ontology; BL-DGE/BL-OME vẫn được phép sinh/sửa primitive khi có gain đủ mạnh.
10. Mọi release mới phải có lý do, delta và con đường rollback/supersession ở cấp public object.

---

## 10. Một đường đọc bảo toàn

Người mới không cần đọc theo chronology. Đường chức năng đề xuất:

```text
1. BL∞ / Reality–GiaTai–UNKNOWN
2. BLEE + Academic Democracy
3. BL-HRD
4. BL-ADN / BL-LOG / BL-CHRONO
5. BL-PCRO / BL-OODP / BLOK
6. BL-NOVO
7. BL-REV / BL-AEGIS
8. RVT / RVP / RVTP / RVL
9. BL-SFRET
10. OPT-HKRP
11. OHAS
12. KAT
13. BL-PIRAL / SRS
14. BL-CPR
15. BL-CONSERVE / BL-OAP
```

Đây là reading route, **không phải tuyên bố rằng object số 1 sinh ra object số 2 trong lịch sử**.

---

## 11. Falsifier / failure conditions của Hệ Bảo Toàn

`BL-CONSERVE` thất bại nếu việc áp dụng nó làm xảy ra một trong các trường hợp:

- không thể reconstruct tại sao state của object thay đổi;
- unification làm mất identity hoặc contradiction quan trọng;
- preservation queue bị biến thành truth certification;
- provenance bị dùng để thay evidence;
- open publishing làm adverse evidence bị chìm dưới volume;
- status model tạo false precision;
- machine graph và human page mô tả hai hệ khác nhau;
- cultural/world anchors bị viết như stereotype bất biến;
- public version mới xóa lịch sử của bản cũ;
- conservation cost lớn hơn giá trị thông tin được giữ mà không có cơ chế nén/phân tầng.

Do đó Hệ Bảo Toàn cũng phải bị audit, sửa, thu hẹp hoặc supersede nếu thực tại và vận hành chứng minh nó tạo nhiều epistemic debt hơn giá trị.

---

## 12. Mệnh đề ngắn nhất

> **Một hệ tri thức chỉ thật sự tiến hóa khi nó có thể thay đổi mạnh mà vẫn nhớ chính xác nó đã thay đổi từ đâu, vì sao, bằng bằng chứng nào, và phần nào vẫn chưa biết.**

Và với xuất bản học thuật:

> **Mọi người có thể được mở quyền đưa một object đủ cấu trúc vào ánh sáng; không ai được mở quyền bắt thực tại phải đồng ý với object đó.**
