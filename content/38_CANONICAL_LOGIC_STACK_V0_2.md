# 38 — Canonical Logic Stack v0.2

Đây là bản ánh xạ tuần tự ngắn nhất của toàn hệ. Nó không thay thế các chương chi tiết; nó cung cấp **đường đi canonical** để người đọc, crawler hoặc AI hiểu tại sao các lớp sinh ra và nối với nhau.

## L0 — Total Reality / system boundary

BL∞ bắt đầu bằng ký hiệu Tổng Thực Tại `Ω` và embedded observer `A ⊆ Ω`.

Điểm xuất phát không phải “mọi thứ đều có thể”, mà là:

\[
Boundary(Knowledge_A)\not\equiv Boundary(\Omega)
\]

khi chưa có closure proof.

Assets chính: **BL-EB, BL-OO**.

## L1 — Representation

Nếu một representation thực sự được tạo bởi embedded agent, sự kiện tạo và trạng thái mang representation thuộc system đang xét:

\[
Generate_A(r)\Rightarrow Event(r)\in\Omega
\]

nhưng:

\[
Existence(Representation_r)\not\Rightarrow Actuality(Referent_r)
\]

Asset chính: **BL-RA**.

## L2 — Reachability / constructibility

BL∞ chuyển từ câu hỏi “x có đang tồn tại?” sang:

\[
x\in Reach(x_0,U)?
\]

Capability repertoire `U` có thể thay đổi; tool có thể sinh tool, vì vậy reachable set là dynamic.

Assets: **BL-GR, BL-RCE, BL-RCG**.

## L3 — Observation filter + open ontology

Observed reality là output qua causal/access/detection/cognitive filters:

\[
O_A(\Omega)=F_A(\Omega)
\]

nên sample quan sát không được mặc định là exhaustive ontology.

Assets: **BL-OFB, BL-OO**.

## L4 — Environmental absorption + Optimizer cognition

Agent học không chỉ qua formal instruction mà còn bằng embedded exposure:

\[
M_{t+1}=Update(M_t,Observe(A,E_t))
\]

Breadth cung cấp primitives; selective depth cung cấp local precision; association/recombination tạo candidate edges; execution đưa candidate ra reality để feedback.

Assets: **BL-EAP, BL-BDRAE, BL-CAF, BL-CRE, BL-BAE, BL-SDF, BL-GSC**.

## L5 — BL-NOVO: ontology về cái mới

Khi prior-art audit xuất hiện, hệ cần phân biệt novelty của primitive với novelty của integration.

\[
N(x)=(N_p,N_r,N_s,N_a,N_f,N_{proc},N_e,N_d)
\]

Các chiều này là **audit dimensions, chưa phải validated numeric scale**.

Assets: **BL-NCI, BL-CNO, BL-RNO, BL-SNO, BL-ANO, BL-FNO, BL-PNO, BL-ENO, BL-IDR, BL-NVM, BL-RDN, BL-NTO, BL-LSI, BL-IFH, BL-FCR, BL-TNI**.

## L6 — Epistemic object: claim thay vì văn bản nguyên khối

Một theory muốn bị đánh chính xác phải được atomize:

\[
Theory\to\{Claim_i\}
\]

mỗi claim có ID, type, scope, dependencies và attack surface.

Research object:

\[
R=(C,P,D,E,V,K,H,S)
\]

với claims, premises, derivations, evidence, provenance, critiques, history và signatures.

Assets: **BL-PCRO, BL-CG, BL-ICO**.

## L7 — Governance + provenance

Publication không được đồng nhất với acceptance. Preserve trước để giảm false-rejection loss, nhưng weight phải kiếm bằng evidence/logic/reproducibility/adversarial survival.

\[
Preserve(H)\not\Rightarrow Accept(H)
\]

\[
UniversalRightToPublish\neq UniversalEpistemicAuthority
\]

Assets: **BL-OODP, BL-PV, BL-TN, BL-ID, BL-CP, BL-LOG, BL-CHRONO, BL-SIGN**.

## L7.5 — BL-HRD: hypothesis-driven reality search

Khi hệ đã có open ontology, claim object, provenance và preservation-before-validation, một câu hỏi mới xuất hiện: **làm thế nào biến khoảng trống của tri thức thành một portfolio giả thuyết có thể kiểm chứng, ưu tiên và học lại?**

BL-HRD thêm một search loop canonical:

\[
Gap
\to Hypothesis
\to Object
\to Preserve
\to Map
\to Depth/Risk
\to Value
\to Portfolio
\to Test
\to RealityVeto
\to State
\to Lineage
\to Learn
\to Recombine
\to Gap'
\]

Hard invariants:

\[
Preserve(H)\not\Rightarrow Believe(H)
\]

\[
RightToPropose=Universal
\]

nhưng:

\[
OpenEntry\neq EqualWeight\neq EqualResources
\]

và:

\[
AIGenerated(H)\not\Rightarrow Evidence(H)
\]

Giá trị hypothesis không chỉ nằm ở xác suất đúng; một hypothesis bị bác vẫn có thể tạo information gain, measurement capability, negative knowledge hoặc recombination value.

BL-HRD phân tầng reality depth từ `L0` tới `L5`; depth/risk càng cao thì evidence burden, safety burden và reversibility requirement càng tăng. Quyền đề xuất không đồng nghĩa quyền thực thi.

Canonical chain chi tiết: **`content/42_HRD_CANONICAL_LOGIC_CHAIN.md`**.

Assets/objects: **BL-HRD, BL-HRD-LOGIC, Global Hypothesis Commons (protocol composition)**.

## L8 — BL-AEGIS: technical/epistemic armor

Các module được ghép thành shields/reactors/meshes thay vì tồn tại rời rạc.

Mục tiêu không phải làm theory miễn nhiễm phản biện mà là:

\[
CheapNoise\downarrow,\quad AddressableCritique\uparrow,\quad ErrorCorrection\uparrow
\]

Assets: **BL-AEGIS**, cùng các compositions trong Asset Registry.

## L9 — Discovery / indexing

Research object phải được addressable và traceable từ fragment:

\[
Fragment\to ClaimURL\to ClaimID\to Theory\to Origin\to Provenance
\]

v0.2 đưa mỗi claim thành URL canonical riêng. `BL-ORBIT` là canonical name mới cho topology routing này; `BL-SG` được giữ như legacy alias để tránh collision thuật ngữ.

Assets: **BL-IDX, BL-ICO, BL-ORBIT, BL-MXF, BL-MGP, BL-ORB, BL-CDS, BL-L10N**.

## L10 — Social pilot

Public reaction là data về transmission/understanding, không phải truth vote:

\[
Reaction=(Attention,Understanding,ObjectionQuality,Restatement,DerivativeIdeas)
\]

Asset: **BL-SRS**.

## L11 — Deep audit

Sau packaging/index/social exposure, object đi vào audit:

\[
Audit_n\to Finding_n\to Patch_n\to Version_{n+1}
\]

Claim có thể được giữ, hạ cấp, sửa, chia hoặc loại.

Assets: **BL-DAL, BL-MAJ, BL-ARS, BL-LC, BL-EOA**.

## L12 — Release / hypothesis spiral

Với research object thông thường:

\[
Idea
\to Package
\to ClaimGraph
\to Provenance
\to Publish
\to Index
\to Reaction
\to Audit
\to Patch
\to Version
\to Republish
\]

Với BL-HRD, vòng này được nối thêm nhánh reality-search:

\[
Gap
\to HypothesisObject
\to Preservation
\to Verification
\to Evidence
\to RealityVeto
\to Revision/NegativeKnowledge
\to Recombination
\to NewGap
\]

Asset: **BL-PIRAL**, composition với **BL-HRD-LOGIC**.

Đây không phải circular proof. Output của mỗi vòng phải có epistemic delta: evidence, critique, capability, measurement, state transition hoặc structural information mới.

## L13 — Recursion back into cognition/reality

Một critique, tool, falsified hypothesis, measurement capability hoặc finding mới trở lại environment của agent:

\[
Environment_t\to Cognition_t\to Theory/Hypothesis_t\to Action/Test_t\to Environment_{t+1}
\]

Sau đó agent hấp thụ state mới và tiếp tục generation.

Đây là điểm BL∞, Optimizer cognition, BL-HRD và research infrastructure zic-zac vào nhau: **theory sinh technology để kiểm tra theory; hypothesis định hướng measurement; Reality Veto tạo feedback; failure trở thành negative knowledge; technology tạo feedback làm thay đổi cognition; cognition sinh theory/hypothesis/version tiếp theo.**

## Canonical non-claim

Không có bước nào ở trên cho phép suy ra:

\[
SystemComplexity\Rightarrow Truth
\]

hay:

\[
HardToRefute\Rightarrow True
\]

hay:

\[
ManyHypotheses\Rightarrow MoreKnowledge
\]

Architecture tốt chỉ làm claim/hypothesis **dễ định vị, dễ kiểm tra, khó bị bóp méo, dễ sửa và dễ tái sử dụng information gain hơn**.
