# BL-ADN — GIAO THỨC ĐÓNG DẤU ADN BÁCH LÂM ∞ & NỐI TIẾP PHẢ HỆ TRI THỨC

**Tên tiếng Việt:** Giao thức Đóng dấu ADN Bách Lâm ∞ và Nối tiếp Phả hệ Tri thức  
**Parent system:** BL-ADN  
**Loại:** Protocol / Attribution / Continuity / Naming / Provenance  
**Citation ID đề xuất:** `BL-ADN-PT-0001`  
**Trạng thái:** `PROPOSED`  
**Phạm vi:** Toàn bộ nguồn, dự án, hội thoại và hệ thống có liên quan đến Bách Lâm / Lâm Kim Bách / Optimizer khi có đủ bằng chứng về quan hệ và tác giả.

---

# I. MỤC ĐÍCH

Giao thức này thiết lập một luật thống nhất:

> Mọi cấu kiện trí tuệ có nguồn gốc thực sự từ Bách Lâm, nếu chứa tính lập luận, học thuyết, thiết lập, hệ thống, giải cấu, kỹ thuật, tổng hợp hoặc phát triển tri thức mới, phải được nhận diện thành một đơn vị tri thức, được đặt tên, truy nguyên, nối với phả hệ cũ nếu có và mang dấu **ADN BÁCH LÂM ∞** ở cuối.

Dấu `∞` biểu thị **tính liên tục, khả năng phát triển và truy nguyên vô hạn của phả hệ**, không đồng nghĩa cấu kiện đó thuộc hệ học thuật `BL∞`.

Tầng máy luôn phải phân biệt:

```text
lineage = BL
system  = hệ thực tế mà object thuộc về
seal    = ADN BÁCH LÂM ∞
```

Do đó:

```math
Seal_{BL\infty}(x)
\not\Rightarrow
x\in System(BL\infty)
```

mà:

```math
Seal_{BL\infty}(x)
\Rightarrow
Lineage(x)=BL
```

khi và chỉ khi provenance đủ để xác lập quan hệ đó.

---

# II. MỆNH LỆNH HIẾN PHÁP

## Luật 1 — Không để cấu kiện trí tuệ của Bách Lâm trôi thành văn bản vô danh

Nếu một phát ngôn đủ điều kiện trở thành cấu kiện trí tuệ:

```math
QualifyingObject(x)=1
```

và:

```math
LKBOrigin(x)=1
```

thì:

```math
Name(x)+Trace(x)+Relation(x)+Seal(x)
```

là bắt buộc.

---

## Luật 2 — Không biến “có liên quan” thành “do Bách Lâm sáng tạo”

```math
RelatedTo(x,BL)
\not\Rightarrow
AuthoredBy(x,BL)
```

```math
UsedBy(x,BL)
\not\Rightarrow
CreatedBy(x,BL)
```

```math
DiscussedBy(x,BL)
\not\Rightarrow
InventedBy(x,BL)
```

Dấu tác giả chỉ được sử dụng khi có provenance tương ứng.

---

## Luật 3 — AI hình thức hóa không được biến thành câu nói nguyên văn của Bách Lâm

Nếu:

```math
IdeaOrigin(x)=BL
```

nhưng AI đã mở rộng, đặt tên, hệ thống hóa hoặc toán học hóa:

```math
Formalizer(x)=AI
```

thì phải ghi:

```text
origin: Bách Lâm
formalization: AI
```

không được ghi:

```text
verbatim_author: Bách Lâm
```

nếu không có văn bản gốc chứng minh.

---

# III. ĐIỀU KIỆN KÍCH HOẠT

Với mỗi đơn vị nội dung `x`, định nghĩa tám tín hiệu:

```math
A(x)=tính\ lập\ luận
```

```math
T(x)=tính\ lý\ thuyết/học\ thuyết
```

```math
C(x)=tính\ thiết\ lập/cấu\ hình/quy\ tắc
```

```math
S(x)=tính\ hệ\ thống/kiến\ trúc
```

```math
D(x)=tính\ giải\ cấu/phân\ biệt\ bản\ chất
```

```math
N(x)=tính\ mới\ đối\ với\ corpus
```

```math
K(x)=tính\ kỹ\ thuật/cơ\ chế/phương\ pháp
```

```math
Y(x)=tính\ tổng\ hợp/tái\ cấu\ trúc
```

Tạo:

```math
Q(x)=A\lor T\lor C\lor S\lor D\lor N\lor K\lor Y
```

Một phát ngôn phải được đóng ADN khi:

```math
\boxed{
Stamp(x)=LKBOrigin(x)\land Q(x)
}
```

Tức chỉ cần **ít nhất một** trong tám thuộc tính xuất hiện, với điều kiện nguồn gốc Bách Lâm đã đủ bằng chứng.

---

# IV. “MỚI” KHÔNG ĐỒNG NGHĨA “CHƯA AI TRÊN THẾ GIỚI NGHĨ RA”

Phải tách:

```math
NewToCorpus(x)
```

khỏi:

```math
NovelInWorld(x)
```

Do đó:

```math
NewToCorpus(x)=1
```

có thể kích hoạt việc tạo SEED mới.

Nhưng:

```math
NovelInWorld(x)=1
```

chỉ được tuyên bố sau prior-art audit.

Không được biến dấu ADN thành chứng nhận tính độc sáng.

```math
ADNSeal
\neq
NoveltyProof
\neq
TruthProof
```

---

# V. CỔNG TÁC GIẢ

Mỗi object phải được phân vào một trong các trạng thái nguồn gốc sau.

### 1. `LKB_DIRECT`

Nội dung được Bách Lâm trực tiếp phát biểu, viết, ra quyết định hoặc xác lập.

```text
provenance: DIRECT_SELF_STATEMENT
authorship: Bách Lâm
```

Được đóng dấu đầy đủ.

---

### 2. `LKB_ORIGIN_AI_FORMALIZED`

Ý lõi, mệnh đề, cơ chế hoặc chỉ đạo đến trực tiếp từ Bách Lâm; AI chỉ làm nhiệm vụ:

- đặt tên;
- chuẩn hóa;
- hệ thống hóa;
- toán học hóa;
- chuyển thành code;
- nối quan hệ;
- mở rộng diễn giải có kiểm soát.

Ghi:

```text
originator: Bách Lâm
formalizer: AI
provenance:
  - DIRECT_SELF_STATEMENT
  - NEW_FORMALIZATION
```

Được đóng ADN Bách Lâm nhưng **phải hiển thị vai trò formalization khi cần truy nguyên đầy đủ**.

---

### 3. `AI_SYNTHESIS_FOR_BL`

AI tự đề xuất nội dung mới dựa trên hệ Bách Lâm nhưng chưa có bằng chứng Bách Lâm đã đưa ra hoặc chấp thuận.

```text
provenance: SYNTHESIS
authorship: AI-generated candidate
lineage_binding: candidate
```

Không được tự động coi là thành quả của Bách Lâm.

Trạng thái:

```text
CANDIDATE_FOR_BL_LINEAGE
```

Sau khi Bách Lâm xác lập, sửa, tiếp nhận hoặc biến nó thành cấu kiện riêng, quan hệ mới được cập nhật phù hợp.

`APPROVED_BY` cũng không tự động đồng nghĩa `AUTHORED_BY`.

---

### 4. `EXTERNAL_DERIVED`

Có nguồn từ người/hệ bên ngoài.

Phải giữ:

```text
DERIVED_FROM
INSPIRED_BY
EXTENDS
CRITIQUES
CONTRADICTS
```

tùy trường hợp.

Tuyệt đối không đổi tên rồi gắn thành phát minh của BL.

---

### 5. `UNKNOWN`

Chưa đủ dữ liệu.

```text
authorship: UNKNOWN
```

Không đóng dấu tác giả.

Giữ lại làm candidate để truy nguyên sau.

---

# VI. CÁI GÌ PHẢI ĐƯỢC ĐÓNG DẤU?

Bao gồm nhưng không giới hạn:

- mệnh đề;
- luận điểm;
- chuỗi lập luận;
- định nghĩa mới;
- distinction mới;
- nguyên lý;
- hypothesis;
- mô hình;
- phương pháp;
- kỹ thuật;
- protocol;
- framework;
- kiến trúc;
- hệ thống;
- ontology;
- thiết lập vận hành;
- cơ chế ra quyết định;
- quy tắc quản trị;
- cơ chế kiểm định;
- cơ chế phản biện;
- cách tổ chức con người;
- chiến lược;
- thiết kế quy trình;
- công nghệ tổ hợp;
- lời giải cấu một khái niệm;
- correction làm thay đổi hệ;
- tổng hợp nhiều mệnh đề thành cấu trúc mới;
- phát triển mới từ cấu kiện cũ;
- cơ chế mới xuất hiện trong quá trình tranh luận;
- một ẩn dụ nếu nó chứa cơ chế nhận thức có khả năng tái sử dụng;
- reasoning chain đủ độc lập để dùng lại.

---

# VII. CÁI GÌ KHÔNG TỰ ĐỘNG ĐÓNG DẤU?

Không cần tạo object chỉ vì Bách Lâm đã nói ra.

Ví dụ:

- chào hỏi;
- câu hỏi thông tin thông thường;
- yêu cầu sửa chính tả;
- lựa chọn giao diện nhất thời;
- “đổi ảnh này”;
- “CTR là gì?”;
- mô tả sự kiện bên ngoài mà không tạo thêm luận điểm;
- trích lời người khác;
- dữ liệu thực tế chưa qua thao tác nhận thức đáng kể.

Tuy nhiên một chỉ đạo vận hành tưởng nhỏ vẫn phải đóng dấu nếu nó thiết lập:

```text
rule
mechanism
standard
workflow
governance
constraint
architecture
```

có khả năng tái sử dụng cho toàn hệ.

---

# VIII. ĐẶT TÊN BẮT BUỘC

Nếu phát ngôn đủ điều kiện nhưng chưa có tên:

```math
NameRequired(x)=1
```

Tên phải sinh từ:

```math
Reality
\rightarrow
Essence
\rightarrow
Mechanism
\rightarrow
Scope
\rightarrow
Class
\rightarrow
Name
```

Công thức:

```math
\boxed{
N(x)=MinimalUniqueExpression
(Essence,Mechanism,Scope,Class)
}
```

Không làm:

```math
CoolName\rightarrow ép\ nội\ dung
```

---

## Ưu tiên đặt tên

1. Nếu Bách Lâm đã trực tiếp đặt tên → giữ tên đó.
2. Nếu tên cũ tồn tại → ưu tiên tên canonical hiện hành.
3. Nếu là phần phát triển từ object cũ → không vội tạo học thuyết mới.
4. Nếu chưa có tên → máy đề xuất **tên mô tả tối thiểu**.
5. Acronym mới chỉ được tạo khi object đủ độ ổn định và cần sử dụng lâu dài.

---

# IX. NỐI VỚI CÁI CŨ TRƯỚC KHI TẠO CÁI MỚI

Mỗi object mới phải trải qua:

```math
NewUnit
\rightarrow
SearchHistory
\rightarrow
SemanticMatch
\rightarrow
RelationClassify
\rightarrow
ReuseOrMint
```

Các khả năng:

### `SAME_OBJECT`

Cùng bản chất, chỉ diễn đạt lại.

Không mint object mới.

```math
Restatement\rightarrow sameObjectAs
```

---

### `REFINES`

Làm chính xác hơn object cũ.

```math
x_{t+1}=Refine(x_t)
```

Tăng version.

---

### `EXTENDS`

Giữ lõi cũ nhưng thêm phạm vi, cơ chế hoặc năng lực.

```math
Old\rightarrow EXTENDS\rightarrow New
```

---

### `DERIVED_FROM`

Cấu kiện mới suy ra trực tiếp từ một hoặc nhiều cấu kiện cũ.

---

### `IMPLEMENTS`

Biến nguyên lý/học thuyết thành quy trình, phần mềm, SOP, code hoặc tổ chức thực tế.

---

### `GENERALIZES`

Mở một cơ chế từ miền hẹp lên miền rộng hơn.

---

### `SPECIALIZES`

Biến một nguyên lý rộng thành dạng chuyên biệt.

---

### `CONTRADICTS`

Mâu thuẫn thực sự.

Không được cố hợp nhất giả.

---

### `SUPERSEDES`

Phiên bản mới được xác lập để thay thế phiên bản cũ.

Cái cũ không bị xóa.

```math
Superseded\neq Deleted
```

---

### `INSPIRED_BY`

Chỉ tạo cảm hứng, không đủ để tuyên bố dẫn xuất.

Phải phân biệt:

```math
INSPIRED_BY\neq DERIVED_FROM
```

---

# X. TRẠNG THÁI VÒNG ĐỜI

Mọi cấu kiện mới đi qua:

```text
INTAKE
↓
SEED
↓
CANDIDATE
↓
FORMALIZED
↓
PROPOSED
↓
AUDITED
↓
CANONICAL
```

hoặc:

```text
REJECTED
MERGED
SUPERSEDED
RETRACTED
REFUTED
```

Không phải câu nào có dấu ADN cũng đã trở thành “học thuyết”.

Dấu ADN chứng minh:

> cấu kiện đã được nhận diện và truy nguyên.

Nó không chứng minh:

> cấu kiện đúng.

---

# XI. CÚ PHÁP DẤU ADN HIỂN THỊ

## Dạng đầy đủ

```text
⟦ ADN BÁCH LÂM ∞
NAME: <canonical_name>
CLASS: <object_class>
LINEAGE: BL
RELATION: <NEW | EXTENDS | REFINES | DERIVED_FROM | ...>
PROVENANCE: <provenance>
STATE: <lifecycle_state>
VERSION: <version>
ID: <uid/citation_id>
⟧
```

Dấu luôn nằm **sau đơn vị tri thức**.

---

## Dạng gọn dùng trong hội thoại

```text
〔ADN BÁCH LÂM ∞ · <TÊN> · <CLASS> · <RELATION> · <STATE> · <ID>〕
```

Ví dụ:

```text
〔ADN BÁCH LÂM ∞ · Nguyên lý Giác quan Thăm dò · PR · SEED · BL-O-...〕
```

Nếu là phát triển từ cấu kiện cũ:

```text
〔ADN BÁCH LÂM ∞ · Nguyên lý Giác quan Thăm dò · PR · EXTENDS BL-O-00001231 · v0.2〕
```

---

# XII. NẾU AI HÌNH THỨC HÓA

Dạng dấu mở rộng:

```text
〔ADN BÁCH LÂM ∞
· <NAME>
· ORIGIN: BÁCH LÂM
· FORMALIZATION: AI
· PROVENANCE: DIRECT_SELF_STATEMENT + NEW_FORMALIZATION
· <STATE>
· <ID>
〕
```

Điều này bảo vệ đồng thời hai thứ:

```math
AttributionIntegrity
+
IntellectualContinuity
```

Không để AI chiếm nguồn của Bách Lâm.

Cũng không biến phần AI tự suy diễn thành phát ngôn giả của Bách Lâm.

---

# XIII. MỘT OUTPUT CÓ NHIỀU MỆNH ĐỀ

Không đóng một con dấu chung vào cuối một bài dài nếu bài chứa nhiều object độc lập.

Máy phải segment:

```math
Output
\rightarrow
Unit_1+Unit_2+\dots+Unit_n
```

Mỗi `Unit_i` được kiểm tra riêng.

Nếu các đơn vị chỉ là thành phần của cùng một hệ thống:

```text
MASTER OBJECT
├── PR-01
├── PR-02
├── MT-01
└── TC-01
```

có thể dùng một dấu master + registry các subobject.

Nếu các mệnh đề có khả năng sống độc lập, phải có ADN riêng.

---

# XIV. HÀM TOÁN HỌC TỔNG QUÁT

Với một phát ngôn `x`:

```math
L(x)\in\{0,1\}
```

= có đủ bằng chứng nguồn gốc Bách Lâm.

Và vector:

```math
\vec q(x)=
[A,T,C,S,D,N,K,Y]
```

với mỗi thành phần:

```math
q_i\in\{0,1\}
```

Đặt:

```math
I(x)=
\begin{cases}
1,&\sum q_i\ge1\\
0,&otherwise
\end{cases}
```

Khi đó:

```math
\boxed{
ADNRequired(x)=L(x)\cdot I(x)
}
```

---

## Hàm liên tục

Sau khi xác định cần ADN:

```math
Parent(x)
=
\arg\max_{o\in Registry}
Similarity(x,o)
```

Nhưng:

```math
Similarity
```

chỉ dùng để tìm candidate.

Nó không được tự quyết quan hệ tác giả hoặc nguồn gốc.

Quan hệ cuối cùng:

```math
Relation(x,o)
=
f(Semantics,Mechanism,Scope,History,ExplicitEvidence)
```

---

# XV. ĐỘ LIÊN QUAN

Có thể dùng các mức routing:

```yaml
explicit_relation: 0.90
canonical_binding: 0.80
verified_derivation: 0.60
conceptual_overlap: 0.35
style_only: 0.15
retain_candidate_at: 0.10
```

Nhưng:

```math
StyleSimilarity
\not\Rightarrow
Authorship
```

Một câu “nghe rất Optimizer” chỉ đủ để máy tìm kiếm thêm.

Không đủ để đóng dấu Bách Lâm.

---

# XVI. PRIORITY VÀ BẢO VỆ THÀNH QUẢ

Mỗi object được đóng ADN nên lưu:

```text
event_time
recorded_time
source_ref
actor
raw_content
canonical_summary
origin_relation
parent_objects
version
content_hash
evidence
```

Có thể tạo:

```math
FP_{x,t}
=
SHA256(
UID_x
\Vert
ContentHash_t
\Vert
ProvenanceRoot_t
\Vert
RelationRoot_t
\Vert
FP_{x,t-1}
)
```

Nhưng:

```math
Hash\neq AuthorshipProof
```

```math
Timestamp\neq NoveltyProof
```

Hash và timestamp tạo **dấu vết bảo vệ**, không thay thế điều tra nguồn gốc.

---

# XVII. QUY TẮC KHÔNG XÓA LỊCH SỬ

```math
Rename\Rightarrow AliasHistory
```

```math
Correction\Rightarrow VersionDelta
```

```math
Merge\Rightarrow MergeRecord
```

```math
Split\Rightarrow DerivedObjects
```

```math
Contradiction\Rightarrow ConflictEdge
```

```math
Supersede\Rightarrow PreserveOldVersion
```

```math
Refutation\Rightarrow StatusChange
```

Không được viết lại quá khứ để tạo cảm giác hệ lúc nào cũng đúng.

ADN Bách Lâm ∞ phải ghi cả:

```text
phát kiến
sai lầm
phản biện
correction
thay đổi
hủy bỏ
hậu duệ
```

---

# XVIII. MACHINE-READABLE KERNEL

```yaml
schema: "BL-ADN-SEAL/1.0"

protocol:
  parent_system: "BL-ADN"
  canonical_name_vi: "Giao thức Đóng dấu ADN Bách Lâm ∞ và Nối tiếp Phả hệ Tri thức"
  citation_id_proposed: "BL-ADN-PT-0001"

identity:
  lineage: "BL"
  human_identity: "Lâm Kim Bách"
  authorial_identity: "Bách Lâm"
  public_system_identity: "Optimizer"

seal:
  display_name: "ADN BÁCH LÂM ∞"
  meaning:
    - lineage_trace
    - intellectual_continuity
    - provenance_binding
    - version_continuity
  does_not_imply:
    - membership_in_BLINF_system
    - truth
    - novelty
    - exclusive_authorship_without_evidence

activation:
  require_lkb_origin: true

  qualifying_dimensions:
    argumentative: true
    theoretical: true
    configurative: true
    systemic: true
    deconstructive: true
    new_to_corpus: true
    technical: true
    synthetic: true

  logical_rule: >
    stamp = lkb_origin AND
    (argumentative OR theoretical OR configurative OR systemic OR
     deconstructive OR new_to_corpus OR technical OR synthetic)

authorship:
  require_explicit_evidence: true

  states:
    LKB_DIRECT:
      stamp: true
      attribution: "AUTHORED_BY"
      provenance:
        - DIRECT_SELF_STATEMENT

    LKB_ORIGIN_AI_FORMALIZED:
      stamp: true
      attribution: "ORIGINATED_BY_LKB"
      formalizer: "AI"
      provenance:
        - DIRECT_SELF_STATEMENT
        - NEW_FORMALIZATION

    AI_SYNTHESIS_FOR_BL:
      stamp_as_lkb_authorship: false
      state: CANDIDATE
      provenance:
        - SYNTHESIS

    EXTERNAL_DERIVED:
      stamp_as_lkb_authorship: false
      preserve_external_provenance: true

    UNKNOWN:
      stamp_as_lkb_authorship: false
      review_required: true

naming:
  mandatory_when_qualified: true
  formula: "MinimalUniqueExpression(Class, Essence, Mechanism, Scope)"
  preserve_user_given_name: true
  search_existing_before_mint: true
  create_acronym_automatically: false

continuity:
  search_registry_first: true

  relation_vocabulary:
    - SAME_OBJECT_AS
    - REFINES
    - EXTENDS
    - DERIVED_FROM
    - DEPENDS_ON
    - IMPLEMENTS
    - GENERALIZES
    - SPECIALIZES
    - CONTRADICTS
    - SUPERSEDES
    - INSPIRED_BY
    - CORRECTED_BY
    - APPROVED_BY
    - REJECTED_BY

  rules:
    same_semantic_object: "reuse_uid_or_version"
    refinement: "increment_version"
    extension: "new_object_or_version_with_EXTENDS_edge"
    contradiction: "preserve_conflict"
    replacement: "SUPERSEDES_without_deletion"
    external_origin: "preserve_external_attribution"

lifecycle:
  states:
    - INTAKE
    - SEED
    - CANDIDATE
    - FORMALIZED
    - PROPOSED
    - AUDITED
    - CANONICAL
    - MERGED
    - SUPERSEDED
    - REJECTED
    - REFUTED
    - RETRACTED

output:
  placement: "end_of_qualifying_knowledge_unit"

  compact_template: >
    〔ADN BÁCH LÂM ∞ · {canonical_name} · {class}
    · {relation} · {state} · {id}〕

  full_template: >
    ⟦ ADN BÁCH LÂM ∞ |
    NAME={canonical_name} |
    CLASS={class} |
    LINEAGE=BL |
    RELATION={relation} |
    PROVENANCE={provenance} |
    STATE={state} |
    VERSION={version} |
    ID={id} ⟧

provenance:
  never_convert_ai_synthesis_to_lkb_quote: true
  never_convert_relation_to_authorship: true
  preserve_raw_source: true
  preserve_conflicts: true
  preserve_superseded_versions: true

truth:
  reality_veto: true
  rules:
    - "seal != truth"
    - "seal != novelty"
    - "timestamp != novelty"
    - "hash != authorship_proof"
    - "approval != authorship"
    - "style != identity"
    - "relation != authorship"

integrity:
  hash_algorithm: SHA256
  hash_versions: true
  preserve_parent_fingerprint: true
```

---

# XIX. PSEUDOCODE THỰC THI

```python
def process_unit(unit, context, registry):

    actor = resolve_actor(unit, context)
    provenance = resolve_provenance(unit, context)

    lkb_origin = verify_lkb_origin(
        actor=actor,
        provenance=provenance,
        explicit_evidence=context.evidence
    )

    dimensions = detect_dimensions(
        unit,
        keys=[
            "argumentative",
            "theoretical",
            "configurative",
            "systemic",
            "deconstructive",
            "new_to_corpus",
            "technical",
            "synthetic",
        ],
    )

    qualifies = any(dimensions.values())

    if not (lkb_origin and qualifies):
        return register_without_lkb_authorship_if_needed(unit)

    candidates = registry.search_semantic(unit)

    parent, relation = classify_continuity(
        unit=unit,
        candidates=candidates,
        provenance=provenance,
    )

    if relation == "SAME_OBJECT_AS":
        obj = update_existing_object(parent, unit)

    elif relation == "REFINES":
        obj = create_new_version(parent, unit)

    else:
        obj = mint_or_register_object(
            unit=unit,
            relation=relation,
            parent=parent,
        )

    obj.name = derive_or_preserve_name(
        unit=unit,
        existing=obj.name
    )

    obj.lineage = "BL"
    obj.provenance = provenance

    obj.fingerprint = build_fingerprint(obj)

    seal = render_bl_infinity_adn_seal(obj)

    return unit + "\n\n" + seal
```

---

# XX. NGUYÊN TẮC ROUTING QUAN TRỌNG

Trình tự bắt buộc:

```text
PHÁT NGÔN
↓
AI CÓ PHẢI BIẾT AI NÓI KHÔNG?
↓
NGUỒN GỐC CÓ ĐỦ BẰNG CHỨNG KHÔNG?
↓
CÓ CHỨA CẤU KIỆN TRÍ TUỆ KHÔNG?
↓
TÁCH THÀNH OBJECT
↓
TÌM OBJECT CŨ
↓
NỐI NẾU NỐI ĐƯỢC
↓
ĐẶT TÊN NẾU CHƯA CÓ
↓
PHÂN CLASS
↓
GẮN PROVENANCE
↓
GẮN VERSION
↓
ĐÓNG ADN CUỐI
↓
CARRY FORWARD VÀO GRAPH
```

Không làm:

```text
Thấy câu hay
→ đặt tên thật kêu
→ gắn Bách Lâm
→ tuyên bố phát minh.
```

---

# XXI. LUẬT “PHÁT TRIỂN THÌ NỐI, KHÔNG SINH HỆ MỚI VÔ TỘI VẠ”

Một nguyên tắc quan trọng của toàn hệ:

```math
\boxed{
ReuseRelation > MintNewObject > MintNewSystem
}
```

Tức ưu tiên:

1. nối với object cũ;
2. version object cũ;
3. tạo object con;
4. tạo framework mới;
5. chỉ tạo system/học thuyết mới khi thực sự có một kiến trúc độc lập đủ lớn.

Nhờ vậy ADN không biến thành máy đẻ tên.

Nó trở thành máy giữ **liên tục tư tưởng**.

---

# XXII. HÀM NÉN TOÀN GIAO THỨC

Có thể nén toàn bộ chỉ lệnh này thành:

```math
\boxed{
BLOrigin
+
IntellectualStructure
\rightarrow
Identify
\rightarrow
Name
\rightarrow
Trace
\rightarrow
Link
\rightarrow
Version
\rightarrow
Seal
\rightarrow
CarryForward
}
```

Trong đó:

```math
\boxed{
Seal\neq OwnershipMagic
}
```

mà:

```math
\boxed{
Seal=
IdentityBinding+
Provenance+
Continuity+
Traceability
}
```

Và:

```math
\boxed{
OldKnowledge
+
NewCognition
\rightarrow
LinkedDevelopment
}
```

không phải:

```math
OldKnowledge
+
NewCognition
\rightarrow
DisconnectedNewTheory
```

---

# XXIII. MỆNH LỆNH MÁY RÚT GỌN

```text
FOR every knowledge unit x:

IF explicit evidence binds intellectual origin of x to Bách Lâm
AND x contains argument, theory, configuration, system design,
deconstruction, corpus-new cognition, technical mechanism,
or meaningful synthesis:

    IDENTIFY x
    SEARCH ancestors
    CLASSIFY relation
    PRESERVE source
    NAME x
    ASSIGN/MAP UID
    LINK historical graph
    LINK logical graph
    LINK adversarial graph when applicable
    VERSION x
    HASH x
    APPEND ADN BÁCH LÂM ∞ seal
    CARRY x forward into unified registry

ELSE:
    DO NOT fabricate Bách Lâm authorship.

IF AI formalizes Bách Lâm-origin material:
    preserve Bách Lâm as origin
    preserve AI as formalizer
    never convert AI wording into a verbatim Bách Lâm quote.

IF new material develops an old object:
    connect before minting.

IF evidence contradicts attribution or doctrine:
    reality/evidence vetoes the seal claim.
```

---

# XXIV. CÂU HIẾN PHÁP CUỐI

**Bất cứ cấu kiện trí tuệ nào thực sự sinh ra từ Bách Lâm đều không được để mất tên, mất nguồn, mất quan hệ hay mất lịch sử; cái mới phải biết mình nối từ đâu, cái cũ phải biết mình đã biến đổi thế nào, AI được phép hình thức hóa nhưng không được đánh tráo nguồn gốc, và dấu ADN Bách Lâm ∞ chỉ có giá trị khi nó truy nguyên được về thực tại.**

```math
\boxed{
Không\ đánh\ dấu\ để\ chiếm\ hữu;
đánh\ dấu\ để\ không\ đánh\ mất\ phả\ hệ.
}
```

---

# XXV. CỔNG CÔNG KHAI BL-CPR

## 1. QUYẾT ĐỊNH KIẾN TRÚC

BL-ADN không chọn một trong hai cực:

- công khai toàn bộ tầng kỹ thuật;
- hoặc giấu toàn bộ để người dùng tự khám phá.

Thay vào đó, hệ áp dụng:

~~~math
\boxed{
Public\ Verification
+
Protected\ Runtime
}
~~~

Tên chính sách:

~~~text
BL-CPR — Công khai Hiến pháp, Bảo vệ Runtime
~~~

Lý do:

- khả năng kiểm chứng, phản biện và truy nguyên có lợi cho cộng đồng;
- công khai prompt vận hành, bộ định tuyến, ngưỡng, log riêng tư, khóa và chi tiết khai thác có thể làm tăng sao chép mù, thao túng, tấn công hoặc rò rỉ dữ liệu;
- che giấu cả tiêu chí, bằng chứng và giới hạn sẽ làm hệ mất tính khả kiểm và đi ngược luật thực tại phủ quyết ADN.

## 2. BA LỚP CÔNG KHAI

### P0 — Bắt buộc công khai

- hiến pháp và nguyên tắc vận hành;
- định nghĩa, ontology và giao diện công khai;
- claim registry, nguồn, provenance và lịch sử phiên bản;
- phương pháp đánh giá, phản biện và tiêu chí bác bỏ;
- kết quả audit ở mức đủ kiểm chứng;
- giới hạn, giả định và các lỗi đã biết;
- định danh người khởi nguyên và vai trò hình thức hóa của AI.

### P1 — Công khai có kiểm soát

- ví dụ kỹ thuật đã khử dữ liệu nhạy cảm;
- benchmark và chẩn đoán đã tổng hợp;
- prompt mẫu không chứa logic vận hành sản xuất;
- mô tả kiến trúc đủ để tái kiểm chứng nhưng không phơi ngưỡng phòng thủ;
- báo cáo sự cố sau khi đã vá và qua thời gian trì hoãn hợp lý.

### P2 — Không thuộc bản phát hành công khai

- system prompt và prompt sản xuất nguyên bản;
- router, trọng số, ngưỡng, heuristic chống lạm dụng và rule nội bộ;
- log riêng tư, dữ liệu cá nhân và corpus chưa được phép công bố;
- thông tin xác thực, khóa, secret và cấu hình hạ tầng nhạy cảm;
- playbook red-team chưa vá hoặc chi tiết khai thác có thể tái sử dụng để gây hại;
- dữ liệu chẩn đoán riêng có thể giúp né kiểm soát.

## 3. LUẬT PHÂN LOẠI

Với mỗi cấu kiện kỹ thuật \(x\), chỉ công khai khi:

~~~math
\boxed{
Benefit_{verify}(x)
>
Risk_{abuse}(x)
+
Risk_{privacy}(x)
+
Risk_{security}(x)
}
~~~

Nếu chưa đủ bằng chứng để quyết định, mặc định đưa vào P1 hoặc P2, lập biên bản lý do và đặt lịch xem xét lại; không dùng từ “bí mật” như một cách né phản biện.

## 4. CỔNG PHÁT HÀNH

Mọi bản công khai phải tự động kiểm tra:

1. có đủ chính sách, claim, provenance và version hay chưa;
2. có đường dẫn runtime/private, file môi trường, khóa hay secret hay không;
3. nội dung máy đọc của BL-CPR có thực sự được xuất bản hay chỉ tồn tại trong repo;
4. audit có thất bại thì dừng build và dừng deploy.

~~~text
IF disclosure_audit fails:
    BLOCK public release
ELSE:
    BUILD
    DEPLOY
    RECORD version and evidence
~~~

## 5. KHÁM PHÁ KHÔNG ĐỒNG NGHĨA VỚI CHE GIẤU

Hệ có thể thiết kế nội dung theo nhiều tầng để người đọc đi từ bản tóm tắt đến bằng chứng sâu hơn. Tuy nhiên:

- ranh giới công khai phải được tuyên bố rõ;
- nội dung P0 phải có đường dẫn trực tiếp và máy đọc được;
- không được dùng trải nghiệm “tự khám phá” để giấu giới hạn, nguồn, phản chứng hoặc điều kiện bác bỏ;
- phần P2 được bảo vệ vì an toàn và riêng tư, không được trình bày như bằng chứng cho một claim công khai.

## 6. MỆNH LỆNH MÁY RÚT GỌN

~~~text
FOR every release candidate:
    PUBLISH verification, evidence, provenance, interfaces, limits, and versions.
    SANITIZE controlled examples and aggregate diagnostics.
    EXCLUDE production prompts, routing internals, private logs, credentials,
            private corpora, unpatched exploits, and evasion-enabling details.
    REQUIRE machine-readable BL-CPR policy.
    FAIL CLOSED when the disclosure audit fails.

NEVER treat hidden runtime material as public evidence.
NEVER treat the ADN seal as proof of truth, novelty, ownership, or safety.
~~~

Nguồn chỉ thị trí tuệ của quyết định phân tầng này: **Bách Lâm**. Phần cấu trúc hóa, đặt mã BL-CPR và diễn đạt kỹ thuật trong mục XXV: **AI hình thức hóa**; không phải trích dẫn nguyên văn của Bách Lâm.

---

## SELF-PROVENANCE CỦA CHÍNH TÀI LIỆU NÀY

```yaml
object:
  canonical_name: "Giao thức Đóng dấu ADN Bách Lâm ∞ và Nối tiếp Phả hệ Tri thức"
  parent_system: "BL-ADN"
  class: "PT"

origin:
  intellectual_directive: "Bách Lâm"
  formalization: "AI"
  relation:
    - EXTENDS_BL_ADN
    - IMPLEMENTS_LKB_OMNI_TRACE
  provenance:
    - DIRECT_SELF_STATEMENT
    - SOURCE_DERIVED
    - NEW_FORMALIZATION

status:
  canonicality: PROPOSED
  version: "0.2.0"
```

〔ADN BÁCH LÂM ∞ · Giao thức Đóng dấu ADN Bách Lâm ∞ và Nối tiếp Phả hệ Tri thức · PT · EXTENDS BL-ADN · PROPOSED · v0.2.0〕
