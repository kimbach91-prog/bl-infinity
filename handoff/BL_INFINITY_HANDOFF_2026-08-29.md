# BL∞ / BLOK / BL-AEGIS — MASTER HANDOFF 2026-08-29

## 0. Mục đích của gói này

Đây là gói chuyển giao cho một phiên/mô hình tiếp theo có nhiệm vụ **không viết lại từ đầu**, mà phải tiếp quản đúng toàn bộ research object hiện có, nhận ra phần nào là canonical hiện hành, phần nào là lịch sử phát sinh, phần nào đã bị phản chứng/sửa, phần nào chỉ là extension/speculation, và đặc biệt phải sửa khoảng cách rất lớn giữa **độ sâu thật của hệ suy luận** với **độ nông của website đang public**.

Repository: `kimbach91-prog/bl-infinity`

Public canonical URL: `https://kimbach91-prog.github.io/bl-infinity/`

Current theory version giữ nguyên: `0.2.0-index-pilot`.

Current handoff snapshot parent commit: `dbe1bce81d3db7534f6a7d03f9c6734c2b15750c`.

Gói handoff này là workspace metadata, chưa phải release học thuyết mới.

---

## 1. Chẩn đoán trung tâm: source giàu, public surface nghèo và có rủi ro hiểu sai

Repo hiện không hề thiếu nội dung. Nó đã có 39 chương nội dung `content/00` đến `content/38`, 68 claim objects, 79 named assets, provenance, formalization programme, novelty ontology, adversarial matrix, non-claims, reasoning lineage, machine layer, GitHub Pages, Actions, Discussions/giscus.

Vấn đề nằm ở **cách build và cách ưu tiên thông tin**.

Website hiện tại làm ba việc gây giảm giá trị:

1. Trang chủ chỉ render `content/00_README_FIRST.md`, nên người mới gần như không thấy phần toán học, chuỗi suy luận, novelty ontology, canonical logic stack và lịch sử phản biện đã tạo nên hệ.
2. `theory.html` nối toàn bộ Markdown thành một khối dài mà không phân biệt rõ `canonical hiện hành / historical origin / speculative extension / attack inventory / implementation / governance`. Vì vậy cái đã bị sửa vẫn có thể đứng cạnh cái sửa nó, khiến người đọc tưởng cùng cấp độ chân trị.
3. Claim pages được tạo từ vài field trong `claims.json` — statement, scope, falsifier, dependencies, novelty dimensions — nhưng không mang derivation, assumptions, equation set, countermodels, explanation trail, version delta hay critique resolution. Tức BL-ICO đang **addressable nhưng chưa proof-carrying đủ sâu**.

Đây là lỗi kiến trúc trình bày, không phải bằng chứng rằng research source chỉ có từng ấy.

---

## 2. Nguyên tắc tiếp quản: không coi mọi file trong repo có cùng thẩm quyền semantic

Mô hình tiếp theo phải tạo **canonical precedence ledger** trước khi sửa site.

Tạm dùng thứ tự ưu tiên sau để audit, không phải để xóa lịch sử:

### Tier A — canonical refinements / guardrails mới hơn

- `content/38_CANONICAL_LOGIC_STACK_V0_2.md`
- `content/34_NOVELTY_ONTOLOGY_AND_NESTED_INNOVATION.md`
- `content/29_NONCLAIMS_AND_BOUNDARIES.md`
- `content/23_FORMALIZATION_PROGRAM.md`
- `content/20_CANONICAL_MANIFESTO.md`
- `content/37_POST_ORIGIN_DELTA_REGISTRY.md`
- `audit/02_V0_2_PREFLIGHT_FINDINGS.md`

### Tier B — machine registry cần reconcile

- `claims/claims.json`
- `machine/assets.json`
- `machine/logic-stack.json`
- `machine/novelty-ontology.json`

Các file này rất quan trọng vì index/crawler dùng chúng, nhưng **không được mặc định đúng hơn Tier A nếu có xung đột cross-file**. Hiện đã phát hiện ít nhất một xung đột numbering và một legacy naming mismatch.

### Tier C — origin derivation / chương nền

- `content/01` → `content/19`

Chúng giữ giá trị giải thích lịch sử và nhiều đoạn vẫn canonical, nhưng phải được semantic-diff với Tier A/B. Không được render chúng như thể tất cả formulation cũ vẫn là phát biểu cuối.

### Tier D — provenance / adversarial / implementation history

- `provenance/*`
- `content/24_ADVERSARIAL_MATRIX.md`
- `content/32_REASONING_TO_CLAIM_MAP.md`
- `critiques/*`
- các setup/SEO/technical docs

Đây là lịch sử phát sinh, attack inventory hoặc implementation. Chúng không phải truth layer.

---

## 3. Canonical mathematical spine cần được giữ nguyên tinh thần

Phần dưới không thay thế source; nó là bản đồ để mô hình tiếp theo biết những distinction nào tuyệt đối không được làm phẳng.

### 3.1. Total Reality và embedded observer

Ký hiệu tổng miền đang xét:

\[
\Omega
\]

Agent thực sự thuộc hệ:

\[
A\subseteq\Omega
\]

Điểm phương pháp:

\[
Boundary(Knowledge_A)\not\equiv Boundary(\Omega)
\]

khi chưa có closure/exhaustiveness proof.

Câu này **không chứng minh Ω vô hạn**, cũng không cấp license postulate tùy tiện. Nó chỉ bác phép đồng nhất biên tri thức hiện tại với biên ontology nếu chưa chứng minh closure.

### 3.2. Representation không phải referent

Nếu agent thực sự tạo representation `r`, sự kiện tạo và token/state mang representation thuộc hệ:

\[
Generate_A(r)\Rightarrow Event(r)\in\Omega
\]

nhưng:

\[
Existence(Representation_r)\not\Rightarrow Actuality(Referent_r)
\]

Đây là correction rất quan trọng sau các vòng tranh luận. Website không được tạo cảm giác BL∞ nói “nghĩ ra là ngoài kia có thật”.

### 3.3. Observation non-injectivity / underdetermination

Cho observation map:

\[
O_A:X\to Y_A
\]

Nếu:

\[
\exists x_1\neq x_2:O_A(x_1)=O_A(x_2)
\]

thì output quan sát đó không đủ phân biệt hai state/model.

Bổ đề “vi khuẩn trong ruột” chỉ là trực giác cho cấu trúc này. Nó không chứng minh cosmology cụ thể.

### 3.4. Conceivability phải resource-bounded khi cần

Một skeleton:

\[
\mathcal C_A=Closure_{F_A}(P_A)
\]

và:

\[
\mathcal C_A(B)=\{d\in Closure_{F_A}(P_A):Cost_A(d)\le B\}
\]

Không được nhập nhằng `description`, `coherent model`, `logical possibility`, `physical possibility` và `actuality`.

### 3.5. Reachability / constructibility

Với transition system:

\[
\mathcal S=(X,U,T,O)
\]

reachable set hữu hạn bước:

\[
Reach_n(x_0)=\{x_n:\exists u_1,...,u_n\ T(...T(x_0,u_1),...,u_n)=x_n\}
\]

closure:

\[
Reach^*(x_0)=\bigcup_{n\ge0}Reach_n(x_0)
\]

resource-bounded:

\[
Reach_B(x_0)=\{x:\exists\pi,Cost(\pi)\le B,\pi(x_0)=x\}
\]

Recursive tool growth:

\[
U_{t+1}=U_t\cup G(U_t,K_t,R_t)
\]

Nếu capability cũ được giữ:

\[
Reach(x,U_t)\subseteq Reach(x,U_{t+1})
\]

Đây là conditional monotonicity, không phải lời hứa đời thực rằng capability luôn tăng.

### 3.6. Reachability–conceivability gaps

\[
G_{RC}=\mathcal R-\mathcal C_A
\]

\[
G_{CR}=\mathcal C_A-\mathcal R
\]

\[
I_{RC}=\mathcal R\cap\mathcal C_A
\]

Strong result mong muốn của programme là chứng minh điều kiện nào làm `G_RC ≠ ∅` trong class hệ cụ thể; hiện không được giả vờ rằng bridge metaphysical đó đã proven.

### 3.7. Finite description / larger state candidate

Nếu description system là finite strings:

\[
|\Sigma^*|=\aleph_0
\]

và một candidate state set có cardinality lớn hơn countable, thì finite unique naming không thể cover từng state một-một. Đây là theorem điều kiện; nó không tự chứng minh cardinality thật của Ω.

### 3.8. Observation filter

Một mô hình selection:

\[
P_A(x|observed)=\frac{s_A(x)P_\Omega(x)}{\int s_A(z)P_\Omega(z)dz}
\]

khi normalization hợp lệ.

Ý nghĩa: observed distribution có thể lệch source distribution nếu selection không identity. Nó không cho quyền suy ra arbitrary unseen entities.

### 3.9. Novelty ontology

Binary `mới/không mới` đã bị thay bằng vector audit:

\[
N(x)=(N_p,N_r,N_s,N_a,N_f,N_{proc},N_e,N_d)
\]

Các chiều: primitive, relational, structural, architectural, functional, process, emergent, derivational.

Không giả định orthogonal, không phải validated measurement scale.

Nguyên lý quan trọng:

\[
c_1,...,c_n\in K_t\not\Rightarrow f(c_1,...,c_n)\in K_t
\]

và:

\[
PriorArt(component)\not\Rightarrow PriorArt(system)
\]

nhưng chiều ngược lại cũng phải giữ: nếu đã tồn tại prior system đủ tương đương về topology/function, đổi tên component không tạo novelty thật.

### 3.10. Claim object và research object

Theory phải atomize:

\[
Theory\to\{Claim_i\}
\]

Research object skeleton:

\[
R=(C,P,D,E,V,K,H,S)
\]

với claims, premises, derivations, evidence, provenance, critiques, history, signatures.

Hiện implementation mới hoàn thành tốt phần `C + addressability`, chưa diễn giải đủ `P,D,E,K,H` trên public claim pages.

### 3.11. Critique graph

\[
G_C=(V,E_d,E_a)
\]

Dependency failure chỉ propagate tự động khi dependency logically necessary và không có alternate proof path.

### 3.12. Provenance graph

\[
G_P=(Artifacts,DerivedFrom,SignedBy,TimestampedAt,Transforms)
\]

Integrity không đồng nghĩa truth.

### 3.13. Release spiral

\[
Idea\to Package\to ClaimGraph\to Provenance\to Publish\to Index\to Reaction\to Audit\to Patch\to Version\to Republish
\]

Public reaction là transmission/understanding data, không phải truth vote.

---

## 4. Các lỗi semantic/canonical đã phát hiện trong audit chuyển giao

### CRITICAL-01 — Axiom ID/numbering collision giữa human layer và machine claim registry

`content/03_CORE_AXIOMS.md` dùng chuỗi:

- BL-A01 Nội tại
- BL-A02 Biểu diễn Nội sinh
- BL-A03 Không-đồng-nhất Biên
- BL-A04 Bản thể Mở
- **BL-A05 Khả đạt Động**
- BL-A06 Bộ lọc Quan sát
- BL-A07 Bảo tồn Phát kiến
- BL-A08 Đồng cấp Phản biện
- **BL-A09 Plenitude**
- BL-A10 Hyper-Plenitude

Trong `claims/claims.json`, machine IDs lại có:

- BL-A-001 Nội tại
- BL-A-002 Không-đồng-nhất Biên
- BL-A-003 Bản thể Mở
- BL-A-004 Observation Filter
- **BL-A-005 Plenitude**

Như vậy label `A05/A-005` đang trỏ hai nội dung khác nếu bỏ khác biệt typography. Đây là lỗi identity nghiêm trọng với một hệ tự nhận claim-level addressability.

**Yêu cầu:** trước v0.3 phải tạo canonical ID migration map. Không đổi ID âm thầm. Giữ legacy alias + `superseded_by`/`formerly_known_as` nếu cần để URL cũ không mất provenance.

### CRITICAL-02 — Legacy `Semantic Gravity` vẫn xuất hiện như canonical ở machine claim

Preflight v0.2 đã nói tên `Semantic Gravity` dễ collision và canonical indexing architecture chuyển sang `BL-ORBIT`; `BL-SG` chỉ là legacy alias.

Nhưng `claims/claims.json` vẫn có `BL-PROT-008` title `Semantic gravity`, và `content/32` vẫn liệt kê `Semantic Gravity` trong reasoning history.

`content/32` có thể giữ vì là chronology, nhưng machine/public claim registry phải phân biệt legacy rõ ràng. Không được cho crawler hiểu đây vẫn là canonical term ngang BL-ORBIT.

### CRITICAL-03 — Public `theory.html` flatten canonical + history + speculation + attack inventory

`build.py` render toàn bộ `content/*.md` trừ `00` vào một article duy nhất. Đây là semantic flattening.

Nó làm:

- origin formulations đứng cạnh post-origin corrections;
- optional metaphysics đứng gần core methodological axioms;
- personal/cognitive model đứng trong cùng surface với ontology;
- publication infrastructure đứng cùng surface với metaphysics;
- adversarial matrix xuất hiện như một phần “học thuyết” thay vì attack inventory;
- historical naming có thể được index như current naming.

**Yêu cầu:** v0.3 không được build theory bằng `render_docs(all content)` nữa.

### HIGH-04 — Claim pages quá nông so với BL-PCRO

Mỗi page hiện chỉ có canonical statement, scope, attack surface, dependencies, novelty dimensions, version và URL.

Một claim nghiêm túc cần ít nhất:

- exact statement;
- status + confidence class;
- definitions;
- assumptions;
- formal representation;
- derivation/proof sketch;
- intuitive explanation;
- examples;
- counterexample boundary;
- what it does NOT imply;
- dependencies;
- evidence/prior-art;
- critique history;
- resolution status;
- provenance/source turn;
- version delta;
- machine fields.

Nếu không, BL-ICO chỉ là index card chứ chưa phải claim-level research object.

### HIGH-05 — Website không có math renderer

`build.py` dùng Mistune với table/strikethrough/task_lists; template không include MathJax/KaTeX. `main.css` cũng không có equation treatment.

Do đó công thức LaTeX trong source không được bảo đảm typeset đúng. Đây là lỗi trực tiếp làm phần toán học mà hệ đã xây dựng mất giá trị trên public surface.

**Yêu cầu:** MathJax hoặc KaTeX, automated rendering test và no-JS fallback hợp lý.

### HIGH-06 — Homepage không phô ra mathematical thesis

Home hiện chỉ là `00_README_FIRST.md`. Nó tốt như README nhưng không đủ làm landing page của một research programme.

Home mới phải cho người đọc thấy ngay:

- core research question;
- 5–10 distinctions chính;
- canonical equations;
- claim status ladder;
- logic stack;
- map từ intuition → formalization → critique → version;
- link vào deep sections.

### HIGH-07 — Adversarial matrix không có resolution ledger

`content/24` có 50 hướng tấn công và quy tắc `RejectWithReason / PatchTheory / OpenResearchQuestion`, nhưng public site không hiển thị status của từng attack.

Khi người đọc gặp attack đã được patch nhưng không thấy resolution, họ dễ hiểu nó là lỗi còn nguyên.

**Yêu cầu:** mỗi attack có ID, target claim, state `{open, patched, rejected-with-reason, empirical-pending}`, patch version và canonical response.

### HIGH-08 — Structured provenance quá nén so với lịch sử suy luận thật

`provenance/02_CONVERSATION_LOG_STRUCTURED.md` tự xác nhận đây là structured reconstruction, không phải raw transcript. Preflight cũng cảnh báo raw transcript chưa import/hash.

Đây là lý do chain “đề xuất → bị phản bác → sửa → bị phản bác lần hai → tái định nghĩa” bị mất độ chi tiết.

**Yêu cầu:** nếu phiên tiếp theo có quyền đọc conversation/project context, phải xây **reasoning delta ledger** thay vì chỉ tóm tắt. Không được giả raw transcript nếu không có byte-exact source.

### HIGH-09 — README reading route đã lỗi thời so với post-origin refinements

`content/00` hướng dẫn audit `07 → 13` rồi claims. Nhưng các correction rất quan trọng nằm ở `23`, `29`, `34`, `37`, `38`.

Reading route mới phải bắt đầu từ canonical logic stack và guardrails, sau đó mới quay về origin history.

### MEDIUM-10 — Asset inflation làm hạ tầng lấn át mệnh đề

79 named assets hữu ích cho machine registry, nhưng nếu public UI đưa registry lên ngang hàng quá sớm, người đọc thấy nhiều tên mã trước khi hiểu 5–10 ý cốt lõi. Hiệu ứng là “naming density > explanatory density”.

**Yêu cầu:** public site ưu tiên concept và derivation. Asset code là secondary metadata, có thể mở khi cần.

### MEDIUM-11 — Core theory, Optimizer cognition và research infrastructure chưa tách surface đủ rõ

Ba tầng có liên hệ nhưng không đồng nhất:

1. BL∞ core ontology/epistemology/formalization;
2. Optimizer cognition/method;
3. BLOK/BL-AEGIS infrastructure.

Site mới phải cho người đọc chuyển tầng, không trộn chúng thành một monolith rồi để hạ tầng kỹ thuật làm người đọc tưởng nó là proof cho metaphysics.

### MEDIUM-12 — Optional strong metaphysics cần nằm trong Extensions

Plenitude/Hyper-Plenitude phải được visual-label là extension/speculative và không đứng như tiên đề core mặc định. Formalization programme cũng nói nếu logic/model semantics chưa được khai báo thì plenitude chỉ là metaphysical slogan.

---

## 5. Những điều website mới phải tuyên bố rất rõ là NON-CLAIMS

Giữ tối thiểu các guardrails sau ở vị trí dễ thấy:

- Không: tưởng tượng `x` ⇒ specimen `x` đang tồn tại vật lý.
- Không: open ontology ⇒ arbitrary entity là fact.
- Không: tên BL∞ ⇒ Ω đã chứng minh actual infinity theo cardinal/time/space.
- Không: infinite time ⇒ all states.
- Không: AI đồng ý ⇒ theorem đúng.
- Không: hash/signature ⇒ truth.
- Không: GitHub/index/SEO ⇒ scientific validation.
- Không: component prior art ⇒ toàn architecture không mới.
- Cũng không: component cũ ⇒ architecture chắc chắn mới.
- Không: independent derivation ⇒ historical priority.
- Không: system complexity ⇒ truth.
- Không: hard-to-refute ⇒ true.
- Không: public reaction/support ⇒ truth vote.

---

## 6. Site architecture bắt buộc cho vòng kế tiếp

Không vá CSS nhỏ trên architecture hiện tại. Rebuild semantic information architecture trước.

### Surface 1 — `/` : Research landing

Nội dung:

- BL∞ là gì trong 3 câu;
- core question;
- 6 không gian `O_A, C_A, R_A, R_A*, P_Ω, A_Ω`;
- 5 canonical distinctions;
- canonical logic stack mini-map;
- status: `index pilot`, chưa phải final theorem;
- “What BL∞ does NOT claim”;
- link tới Formal Core, Derivation, Critiques, Infrastructure.

### Surface 2 — `/core/` : Formal Core

Chỉ chứa core definitions/axioms/propositions/theorems đang active.

Tách rõ:

- Definition
- Axiom/methodological rule
- Proposition
- Formal theorem
- Conjecture
- Empirical interface
- Optional extension

### Surface 3 — `/claims/<id>/` : Rich claim object

Schema bắt buộc xem mục 7.

### Surface 4 — `/derivation/` : Reasoning lineage

Hiển thị quá trình sinh mệnh đề:

`intuition → objection → correction → formalization → current claim`.

Đây là nơi giữ các ví dụ vi khuẩn, chó 700 đầu, code nghĩa rộng, academic critique, novelty discussion mà không làm chúng lẫn thành theorem.

### Surface 5 — `/formalization/`

Đưa toàn bộ mathematical programme thành chương có equation rendering thật, assumptions và proof-status.

### Surface 6 — `/extensions/`

Plenitude, hyper-plenitude và các bridge mạnh chưa proven nằm riêng.

### Surface 7 — `/novelty/`

BL-NOVO, vector novelty, nested constituent innovation, reference-domain novelty, independent derivation.

### Surface 8 — `/critique/`

Không chỉ dump Markdown. Có:

- attack ID;
- target claim;
- objection;
- status;
- resolution;
- patch/version;
- discussion link.

### Surface 9 — `/optimizer/`

BDRAE/O-Type, absorption, recursive epistemology. Tách khỏi core BL∞ nhưng giữ crosslinks.

### Surface 10 — `/infrastructure/`

BLOK, BL-AEGIS, PCRO, provenance, indexing, social pilot, release spiral.

### Surface 11 — `/history/`

Origin Build v0.1, post-origin deltas, deprecated names, migration table.

### Surface 12 — `/machine/`

Machine manifest, claims, assets, JSON-LD, llms, dependency graphs.

---

## 7. Rich Claim Object schema cho v0.3

Mỗi claim public phải có cấu trúc tối thiểu:

```yaml
id:
title:
canonical_status:
claim_type:
version_introduced:
version_last_changed:
legacy_ids: []
supersedes: []
superseded_by: null
statement:
plain_language_statement:
scope:
non_implications: []
definitions: []
assumptions: []
formalism:
  equations: []
  logic_regime:
  model_class:
derivation:
  steps: []
  proof_status:
examples: []
counterexamples_or_boundaries: []
falsifiers: []
depends_on: []
supported_by: []
attacked_by: []
critique_resolutions: []
prior_art: []
provenance:
  origin_event:
  source_files: []
  chronology:
novelty:
  reference_domain:
  vector: {}
machine:
  canonical_url:
  jsonld_type:
```

Không bắt mọi field có dữ liệu ngay, nhưng field trống phải hiện `not established`, không được bị thay bằng suy đoán.

---

## 8. Acceptance tests cho semantic build mới

Ngoài structural audit hiện có, bổ sung test:

### Identity tests

- Không có cùng canonical ID trỏ hai statement khác nhau.
- Legacy alias không được index như canonical term.
- Mỗi `superseded` claim có target migration hợp lệ.

### Status tests

- `speculative/extension` không xuất hiện trong core list nếu không có label.
- `theorem` phải có formal environment hoặc status `formalizable`.
- `analogy` không được render trong theorem style.

### Math tests

- Mọi `\[...\]`/`\(...\)` render thành math node hoặc KaTeX/MathJax output trong build test.
- Equation text vẫn có accessible fallback.

### Derivation tests

- Mọi public core claim phải có ít nhất một source/derivation pointer.
- Không có claim page chỉ còn một câu statement nếu claim là proposition/theorem/principle.

### Critique tests

- Mọi resolved objection phải chỉ được hiển thị cùng resolution hoặc link tới resolution.
- Attack inventory không được masquerade thành unresolved defect list.

### Navigation tests

- Home → core claim ≤ 2 clicks.
- Fragment/claim URL → theory → origin/provenance traceable.
- Mobile TOC/search hoạt động.

### Guardrail tests

Fail build nếu xuất hiện các absolute formulations kiểu:

- imagination implies physical actuality;
- infinite time implies every state;
- AI consensus implies truth;
- indexing implies validation;
- prior component automatically defeats system novelty.

---

## 9. Quy trình tái dựng khuyến nghị cho mô hình tiếp theo

### Phase 0 — Freeze

Không phát minh thêm 50 asset mới. Freeze taxonomy trong lúc reconcile.

### Phase 1 — Semantic diff

Đọc theo precedence ledger và tạo bảng:

`object / old formulation / objection / correction / current formulation / source / status`.

Đặc biệt reconcile:

- axiom IDs;
- plenitude position;
- Semantic Gravity → BL-ORBIT;
- origin vs post-origin novelty objects;
- claim status wording.

### Phase 2 — Canonical object model

Biến current knowledge thành structured claim model theo schema mục 7.

### Phase 3 — Derivation recovery

Từ `provenance/02`, `content/32` và conversation context khả dụng, khôi phục reasoning chain chi tiết. Không invent transcript.

### Phase 4 — Formalization expansion

Với mỗi core claim:

- object;
- domain;
- assumptions;
- equation;
- theorem target;
- proof status;
- failure mode;
- bridge to reality.

### Phase 5 — Rebuild renderer

Không dùng one-page Markdown concatenation.

Add:

- MathJax/KaTeX;
- section-aware templates;
- rich claim pages;
- TOC/search;
- version/status badges;
- graph navigation;
- critique status.

### Phase 6 — Machine synchronization

Generate human page, claims JSON, JSON-LD, sitemap, llms and dependency graph từ **một canonical structured source**, tránh human/machine drift.

### Phase 7 — Adversarial semantic audit

Chạy attack matrix nhưng mỗi finding phải route vào claim object và tạo state transition.

### Phase 8 — v0.3 release candidate

Chỉ bump version khi semantic migrations, claim IDs và public UI đã ổn.

---

## 10. Những việc mô hình tiếp theo KHÔNG được làm

1. Không lấy website public hiện tại làm nguồn tri thức đầy đủ nhất.
2. Không lấy file cũ hơn làm canonical chỉ vì nó có tiêu đề “core”.
3. Không xóa lịch sử phản chứng; chuyển nó sang history/derivation/superseded state.
4. Không biến công thức thành trang trí. Mỗi công thức phải có semantics và status.
5. Không gọi proposed principle là theorem.
6. Không đồng nhất framework naming với historical novelty proof.
7. Không dùng prior-art(component) như refutation tự động của architecture.
8. Không dùng “tái tổ hợp” như lá chắn tự động nếu prior system isomorphic đã tồn tại.
9. Không để hạ tầng GitHub/SEO/AI đứng như evidence cho metaphysical truth.
10. Không coi critique attack list là lỗi đã xác nhận.
11. Không làm mất raw uncertainty: cái chưa biết phải ghi chưa biết.
12. Không thêm “giọng AI” dài dòng để che thiếu derivation.

---

## 11. Những thành phần hiện đã khá vững về cấu trúc

- Source separation: content / claims / machine / provenance / critiques / audit.
- Claim IDs và per-claim URL đã được implement ở mức indexing.
- Asset registry và logic stack đã machine-readable.
- GitHub Pages build/deploy đang chạy.
- Discussions + `Page Comments` category đã được tạo; `bl.config.yml` đã có giscus IDs và comments enabled.
- Latest build/deploy trước gói handoff đã success.
- Structural audit kiểm tra uniqueness, dependencies, cycles, required v0.2 claims, forbidden absolute formulations và deployment placeholders.

Nhưng structural green **không** đồng nghĩa semantic consistency green. `audit.py` hiện chưa kiểm tra cross-file claim identity, supersession, naming precedence, math render, derivation completeness hay critique resolution.

---

## 12. Source map tối thiểu phải đọc trước khi sửa theory

### Core origin

- `content/01_ORIGIN_AND_RESEARCH_QUESTION.md`
- `content/02_DEFINITIONS_AND_SPACES.md`
- `content/03_CORE_AXIOMS.md`
- `content/04_FINITE_INSIDE_UNBOUNDED.md`
- `content/05_EMBEDDED_OBSERVER_AND_BACTERIUM.md`
- `content/06_REPRESENTATION_REACHABILITY_ACTUALIZATION.md`
- `content/07_GENERATIVE_REALITY_AND_RECOMBINATION.md`
- `content/08_OBSERVATION_FILTER_AND_SURVIVOR_BIAS.md`

### Cognition/method

- `content/09_COGNITIVE_ABSORPTION_AND_OTYPE.md`
- `content/10_OPTIMIZER_RECURSIVE_EPISTEMOLOGY.md`

### Formal/current correction

- `content/20_CANONICAL_MANIFESTO.md`
- `content/23_FORMALIZATION_PROGRAM.md`
- `content/24_ADVERSARIAL_MATRIX.md`
- `content/29_NONCLAIMS_AND_BOUNDARIES.md`
- `content/32_REASONING_TO_CLAIM_MAP.md`
- `content/34_NOVELTY_ONTOLOGY_AND_NESTED_INNOVATION.md`
- `content/37_POST_ORIGIN_DELTA_REGISTRY.md`
- `content/38_CANONICAL_LOGIC_STACK_V0_2.md`

### Machine/canonical registry

- `claims/claims.json`
- `machine/assets.json`
- `machine/logic-stack.json`
- `bl.config.yml`

### Provenance

- `provenance/00_ORIGIN_TIMELINE.md`
- `provenance/01_REASONING_LINEAGE.md`
- `provenance/02_CONVERSATION_LOG_STRUCTURED.md`
- `provenance/03_RAW_TRANSCRIPT_IMPORT.md`

### Implementation bottleneck

- `scripts/build.py`
- `scripts/audit.py`
- `assets/css/main.css`
- `assets/js/site.js`

---

## 13. Trạng thái hạ tầng tại thời điểm handoff

### GitHub Pages

Build và deploy workflow đã success ở commit trước handoff.

### giscus

Config hiện có:

- repo: `kimbach91-prog/bl-infinity`
- repo_id: `R_kgDOUHWEZQ`
- category: `Page Comments`
- category_id: `DIC_kwDOUHWEZc4DEaRD`
- mapping: `pathname`
- comments enabled: `true`

Người dùng đã cài giscus GitHub App với quyền read/write Discussions. Mô hình tiếp theo nên re-test public comment widget sau khi site cache/deploy ổn định.

### Current build design

- static Python build;
- Mistune Markdown;
- Jinja string template;
- GitHub Pages action;
- no full math renderer;
- no rich client app required.

Không bắt buộc chuyển framework lớn. Có thể giữ static architecture nhưng renderer phải semantic hơn.

---

## 14. Mục tiêu thật của vòng tiếp theo

Không phải “làm trang đẹp hơn”.

Mục tiêu là:

> **Biến toàn bộ chuỗi nhận thức đã được tranh luận, phản chứng, sửa, formalize và đóng gói thành một public research object có cùng độ phân giải với suy luận gốc.**

Một reader phải thấy được:

1. câu hỏi ban đầu;
2. intuition;
3. lỗi interpretation đầu tiên;
4. objection;
5. correction;
6. formulation hiện tại;
7. formal equation;
8. assumption;
9. proof status;
10. boundary/non-claim;
11. dependency;
12. critique;
13. patch/version;
14. provenance.

Nếu website chỉ show statement cuối mà không show đường sinh, nó bỏ mất phần có giá trị nhất của dự án: **cơ chế tự sửa nhận thức và cách một intuition được ép dần thành object có thể kiểm tra.**

---

## 15. Definition of done cho phiên tiếp theo

Chưa được gọi là “đã tái dựng xong” cho tới khi:

- claim ID namespace không còn collision;
- canonical/legacy/superseded rõ ràng;
- BL-ORBIT migration sạch;
- homepage chứa formal spine;
- math render thật;
- mỗi core claim có derivation;
- attack matrix có resolution states;
- history tách khỏi active theory;
- optional metaphysics tách khỏi core;
- human và machine layer sinh từ cùng source;
- audit test semantic mới pass;
- mobile UX đọc paper dài không khó chịu;
- website không còn làm một người đọc nghiêm túc hiểu BL∞ đơn giản hơn hoặc cực đoan hơn formulation hiện tại.

Đó mới là mục tiêu v0.3.
