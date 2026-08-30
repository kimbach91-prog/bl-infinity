# BL-WDRC — Chu kỳ Chưng cất và Cải cách Tuần BL∞

> **UID:** `BL-BLINF-PROT-0001`  
> **Class:** Operational publication protocol  
> **Version:** `0.1.1-pilot`  
> **Status:** `PILOT_ACTIVE` — chưa phải bản cuối hoặc tối ưu nhất  
> **Target surface:** `/critique.html`  
> **Public scope:** BL Infinity và các sáng kiến thiết lập tự do học thuật có quan hệ trực tiếp  
> **Release strategy:** progressive market probe  
> **Cadence:** một chu kỳ mỗi tuần; không ép tạo release khi không có delta đủ chuẩn.

## 1. Mục đích

BL-WDRC biến dòng tri thức mới thành một chu kỳ có thể truy nguyên:

```text
Trace -> Candidate -> Comparison -> Distillation -> Adversarial Audit -> Canonical Delta -> Release
```

Đây không phải cơ chế “đăng thêm nội dung mỗi tuần”. Mục tiêu là làm BL∞ chính xác hơn, ít trùng hơn, ít tự mâu thuẫn hơn và có khả năng dựng ngược cao hơn. Một tuần không có thay đổi đủ chuẩn phải kết thúc bằng **NO_CANONICAL_DELTA**, không bằng một commit tạo nhiễu.

## 2. Trật tự kiến trúc

BL-WDRC dùng thứ tự sau khi đánh giá hoặc cải cách các lớp kỹ thuật:

1. **BL Infinity Kernel** — provenance, registry, versioning, evidence, contradiction, adversarial audit, dependency impact và rollback.
2. **Optimizer** — doctrine và phương pháp suy luận/thực thi.
3. **Lâm Kim Bách Optimizer** — identity/author-brand; không tự động đồng nhất với mọi output trong hệ.
4. **OCANO, OHSIA, OPSE, OTREA, OMOS, ACE và các lớp khác** — subsystem/plugin có chức năng cụ thể.

Subsystem không được đứng ngang Kernel chỉ vì có tên, nhiều tài liệu hoặc đã từng được dùng. Mỗi lớp phải chứng minh chức năng còn sống, ranh giới, dependency và giá trị biên của nó.

### 2.1. Public allowlist

Public surface chỉ nhận các object thuộc ít nhất một trong hai miền:

1. **BL Infinity trực tiếp** — mệnh đề, kiến trúc, Kernel, giao thức, kỹ thuật, test, bằng chứng, provenance, phản biện và lịch sử sửa đổi của BL∞.
2. **Tự do học thuật trực tiếp** — cơ chế bảo vệ quyền nêu giả thuyết, quyền phản biện, quyền giữ bất đồng có trạng thái, khả năng tái lập, minh bạch nguồn, chống chiếm đoạt tác giả và quyền sửa sai bằng bằng chứng.

Object thuộc dự án, thương hiệu, nhân vật hoặc hệ khác không được công bố tại đây chỉ vì có liên hệ với Bách Lâm/Optimizer. Chỉ giữ phần liên hệ tối thiểu khi nó là dependency cần thiết để hiểu hoặc kiểm tra một claim BL∞, và vẫn phải qua BL-CPR.

Mỗi candidate được gán một disclosure class trước khi soạn bản public:

- `OPEN/P0` — đủ an toàn để công bố: claim, lập luận, bằng chứng, falsifier, specification, schema, test vector và reference behavior cần cho tái lập;
- `CONTROLLED/P1` — chỉ công bố mô tả rút gọn hoặc interface khi chi tiết làm lộ lợi thế vận hành hoặc tăng rủi ro;
- `PROTECTED/P2` — không đưa lên public surface: production prompt, routing/ranking nội bộ, private diagnostic, private corpus, dữ liệu riêng, credential, exploit chưa vá hoặc kỹ thuật ảnh hưởng có rủi ro không tương xứng.

Mục tiêu “bảo vệ và phát tán” được thực hiện bằng UID, provenance, timestamp, version, hash, citation surface, test tái lập và lịch sử supersession; việc công bố không tự được mô tả như bằng chứng chân lý, ưu tiên lịch sử tuyệt đối hoặc quyền bảo hộ độc quyền.

### 2.2. Phát hành thăm dò tăng dần

BL∞ dùng **progressive probe**, không dùng big-bang release:

- mỗi release chỉ công bố một lát cắt kỹ thuật hoặc một cụm lập luận có ranh giới;
- lát cắt phải **đủ toàn diện để dùng và phản biện từ đầu đến cuối**, nhưng không giả là bản tối ưu cuối cùng;
- không công bố trước toàn bộ master plan, best-known private implementation hoặc backlog bảo vệ;
- không dùng nhãn `FINAL`, `ULTIMATE`, `COMPLETE` hoặc `OPTIMAL` khi chưa có bằng chứng tương ứng;
- phản ứng thị trường là evidence để cập nhật, không phải phiếu bầu quyết định chân lý;
- ưu tiên tín hiệu chất lượng: phản biện có cấu trúc, thử tái lập, citation đúng, lỗi hiểu sai, prior art, failure mode, chi phí bảo trì và sự cố disclosure; không tối ưu vanity metric hoặc spam index.

Mỗi release pilot phải khai báo: `release_hypothesis`, `public_slice`, `withheld_scope`, `success_signals`, `failure_signals`, `review_date` và `rollback_ref`.

## 3. Nguồn đầu vào

Mỗi chu kỳ chỉ dùng nguồn mà phiên chạy thực sự có quyền truy cập:

- canonical source mới nhất trên `main`;
- trace mới trong Project, chat, file, memory hoặc connected source;
- critique, issue, evidence và prior art công khai đủ gần;
- kết quả build/audit và thay đổi public surface.

Không được tuyên bố “đã quét toàn bộ” nếu coverage không chứng minh được. Không đưa raw private chat, private corpus, credentials, production prompt, routing weight, operator-only diagnostics hoặc exploit payload vào public source.

## 4. Đơn vị tri thức tối thiểu

Mỗi unit được xem xét phải có, khi khả dụng:

- `unit_id`;
- `source_scope`, `source_ref`, `datetime`;
- `actor`, `relation`, `project`, `system`;
- `action_or_claim`, `canonical_summary`;
- `provenance`, `confidence`, `status`;
- `conflicts`, `supersedes`, `linked_units`.

Provenance hợp lệ gồm: `DIRECT_SELF_STATEMENT`, `SOURCE_DERIVED`, `CONVERSATION_DERIVED`, `SYSTEM_CODIFIED`, `EXTERNAL_OBSERVATION`, `SYNTHESIS`, `NEW_FORMALIZATION`, `INFERENCE`, `UNKNOWN`.

**Relation, style và interaction không tự chứng minh identity hoặc authorship.** AI formalization không được đổi thành phát ngôn nguyên văn của Lâm Kim Bách.

## 5. Pipeline bắt buộc

```text
INGEST -> NORMALIZE_NAMES -> ENTITY_RESOLVE -> CLASSIFY_RELATION
-> LABEL_PROVENANCE -> SCORE -> DEDUPLICATE -> VERSION_RESOLVE
-> LINK_GRAPH -> DETECT_CONFLICTS -> SYNTHESIZE_WITHOUT_ERASING_SOURCE
-> ADVERSARIAL_TEST -> RELEASE_DECISION
```

Một candidate không được đi tắt từ ingest sang publication.

## 6. Đặt tên và bảo toàn identity

Tên được sinh theo trục:

```text
Reality -> Object -> Class -> Essence -> Scope -> Function -> Name
```

Quy tắc:

- tên không rộng hơn evidence;
- UID bất biến;
- rename phải giữ `legacy_ids`, `sameAs`, `supersedes` hoặc `superseded_by`;
- component overlap không đồng nghĩa system identity;
- independent derivation không đồng nghĩa historical priority;
- đổi tên không tự tạo novelty;
- collision chưa giải quyết thì giữ `CANDIDATE` hoặc `UNKNOWN`.

## 7. Cổng đối chiếu và thăng cấp

| Gate | Câu hỏi | Fail state |
|---|---|---|
| G0 — Source | Có nguồn và coverage thật không? | `EVIDENCE_REQUIRED` |
| G1 — Identity | Actor/relation/authorship đã phân biệt chưa? | `IDENTITY_UNRESOLVED` |
| G2 — Semantics | Object mới khác gì object hiện có? | `DUPLICATE_OR_AMBIGUOUS` |
| G3 — Naming | Tên/ID có đúng scope và không collision? | `NAMING_HOLD` |
| G4 — Reality | Claim có vượt evidence hoặc nhập nhằng fact/inference? | `DOWNGRADE` |
| G5 — Adversarial | Có sống qua phản chứng, scope và dependency audit? | `REVISE_OR_REJECT` |
| G6 — Disclosure | Có vượt BL-CPR hoặc lộ runtime bảo vệ? | `BLOCK_PUBLICATION` |
| G7 — Build | Human/machine/build checks đồng bộ và xanh? | `RELEASE_BLOCKED` |

Chỉ object vượt đủ cổng cần thiết mới được `CANONICAL`. Cái chưa đủ dữ liệu được giữ lại có điều kiện; không bị xóa và cũng không được giả thành kết luận.

## 8. Cải cách lớp kỹ thuật

Mỗi subsystem được gán đúng một quyết định chính trong chu kỳ:

- `KEEP` — chức năng riêng còn cần và đang hoạt động;
- `REFACTOR` — chức năng đúng nhưng cấu trúc gây drift, trùng hoặc khó kiểm;
- `MERGE` — chức năng bị chia vụn, hợp nhất làm giảm phức tạp mà không mất năng lực;
- `DEMOTE` — vẫn hữu ích nhưng chỉ là module/phép chiếu, không phải lớp lõi;
- `DEPRECATE` — ngừng dùng cho output mới nhưng giữ lịch sử và migration;
- `REJECT` — sai, vô dụng hoặc rủi ro vượt giá trị; giữ reason và evidence.

Mỗi quyết định phải ghi: chức năng, overlap, evidence of utility, complexity cost, dependency impact, rollback và replacement nếu có.

## 9. Semantic diff bắt buộc

Mỗi thay đổi canonical phải có bảng:

```text
Object -> Old Formulation -> Objection -> Correction -> Evidence -> Status -> Downstream Impact
```

BL-REV/BL-AEGIS phải tìm tối thiểu: counterexample, false equivalence, scope creep, identity collision, human–machine drift, hidden assumption, proof-status inflation, self-sealing và disclosure failure.

### 9.1. Hấp thu và phân loại phản biện theo lịch

Mỗi chu kỳ tuần đọc các kênh public mà phiên chạy thực sự truy cập được như GitHub Discussions/giscus, issue, pull request review và nguồn phản biện được dẫn chiếu. Coverage phải được khai báo; không thấy phản biện không đồng nghĩa không có phản biện.

```text
CAPTURE -> SANITIZE -> DEDUPLICATE -> PROVENANCE
-> CLASSIFY -> PRIORITIZE -> LINK_TARGET -> DRAFT_RESOLUTION
-> HUMAN_GATE -> CANONICAL_DECISION
```

“Auto-absorb” chỉ có nghĩa là ghi nhận phản biện vào registry/staging với nguồn và trạng thái. Nó **không** tự biến phản biện thành fact, không tự đổi truth-status và không tự merge vào canon.

Phân loại tối thiểu:

- `SUPPORT_OR_REPLICATION`;
- `LOGIC_OBJECTION`;
- `COUNTEREXAMPLE`;
- `PRIOR_ART`;
- `EVIDENCE_REQUEST`;
- `SCOPE_OR_DEFINITION`;
- `IMPLEMENTATION_DEFECT`;
- `ATTRIBUTION_OR_PROVENANCE`;
- `SECURITY_OR_DISCLOSURE`;
- `NOISE_ABUSE_OR_OUT_OF_SCOPE`.

Trạng thái xử lý: `NEW`, `TRIAGED`, `NEEDS_EVIDENCE`, `ACCEPTED_AS_INPUT`, `REJECTED_WITH_REASON`, `MERGED_INTO`, `OWNER_REVIEW`, `RESOLVED`, `ARCHIVED`.

Ưu tiên lịch:

- `P0` — lộ dữ liệu/rủi ro, gán sai tác giả hoặc claim public sai vật chất: chặn release và đưa ra review ngay;
- `P1` — counterexample, prior art hoặc falsifier có bằng chứng: xử lý trong chu kỳ gần nhất;
- `P2` — làm rõ scope, thuật ngữ, reference implementation hoặc test: đưa vào backlog pilot;
- `P3` — lặp, thiếu bằng chứng, ngoài phạm vi hoặc abuse: lưu reason rồi archive/quarantine.

Phải giữ nguyên phản biện gốc khi hợp lệ, liên kết resolution với objection và lưu before/after delta. Automation được phép thu nhận, phân loại và soạn draft; publication/canonical merge vẫn phải vượt release gate.

## 10. Đồng bộ human–machine

Sửa canonical structured source trước. HTML, claims JSON/JSON-LD, machine graph, provenance, sitemap, `llms.txt` và critique ledger phải được sinh hoặc đồng bộ từ cùng trạng thái nguồn.

`site/critique.html` là build artifact; không được sửa riêng để tạo một bề mặt đẹp nhưng sai source.

## 11. Weekly ledger

Khi có delta đủ chuẩn, `critique.html` phải hiển thị một entry gồm:

```yaml
cycle_id: BL-WDRC-YYYY-Www
date:
source_coverage:
baseline_commit:
public_scope: BL_INFINITY_OR_ACADEMIC_FREEDOM_ONLY
release_slice:
release_hypothesis:
withheld_scope: []
technique_packages: []
critique_intake: []
accepted_units: []
rejected_units: []
subsystem_decisions: []
renames_and_migrations: []
open_conflicts: []
semantic_diff_refs: []
critique_resolutions: []
release_version:
pull_request:
checks:
deployment:
rollback_ref:
human_decisions_required: []
```

Không có canonical delta thì chỉ báo trong kết quả chạy; không ghi heartbeat rỗng vào repository.

## 12. Release gate

1. Tạo branch `weekly/bl-infinity-YYYY-MM-DD`.
2. Commit source canonical và derivative đồng bộ.
3. Mở pull request; không push thẳng `main`.
4. Chạy tối thiểu:
   - `python scripts/audit.py --strict`;
   - `python scripts/disclosure_audit.py --strict`;
   - `python scripts/build.py`.
5. Chỉ merge khi checks xanh, attribution đúng, BL-CPR sạch và không có semantic blocker.
6. Ontology lõi, ID migration lớn, claim bị reject hoặc release major phải chờ quyết định có thẩm quyền.
7. Merge tạo release có thể truy nguyên; rollback dùng commit/release trước, không rewrite lịch sử.

### 12.1. Ngân sách release pilot

Trong một chu kỳ công bố, mặc định tối đa:

- **01 gói kỹ thuật** có `technique_id`, problem, interface, input/output, assumptions, minimal reference mechanism hoặc pseudocode, test vector, limitations, falsifier, provenance và version;
- **01 cụm lập luận/sửa đổi** có semantic diff hoàn chỉnh;
- **03 critique candidates** được triage và liên kết đúng target.

Giới hạn này là change budget, không phải chỉ tiêu phải dùng hết. Nếu delta chưa đủ chuẩn thì giữ staging hoặc kết thúc bằng `NO_CANONICAL_DELTA`.

Bản pilot phải là một **vertical slice** dùng được: nhận diện -> giải thích -> thử nghiệm -> phản biện -> rollback. Tối ưu hiệu năng, mở rộng coverage và các kỹ thuật mạnh hơn được giữ cho các vòng sau dựa trên bằng chứng thu được.

## 13. Definition of done

Một chu kỳ hoàn tất khi:

- coverage được khai báo đúng;
- accepted và rejected delta đều có reason;
- mọi rename có migration;
- subsystem decisions có dependency/rollback;
- critique resolution không tách khỏi objection;
- human và machine layer không drift;
- public surface chỉ thuộc public allowlist và không lộ runtime bảo vệ;
- release không vượt pilot change budget và không tự nhận là bản cuối;
- phản biện đã thu nhận được phân loại nhưng không tự nâng thành canon;
- PR/check/deploy có trạng thái xác minh được;
- UNKNOWN vẫn là UNKNOWN.

---

### BL-ADN provenance stamp

```yaml
unit_id: BL-BLINF-PROT-0001
canonical_name: BL-WDRC — Chu kỳ Chưng cất và Cải cách Tuần BL∞
content_type: operational_protocol
provenance: NEW_FORMALIZATION
relation: REQUESTED_FOR_PROJECT
formalization: AI
authorship_note: not_a_verbatim_statement_of_Lam_Kim_Bach
status: PILOT_ACTIVE
version: 0.1.1-pilot
date: 2026-08-30
```
