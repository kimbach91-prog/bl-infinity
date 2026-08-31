# 34 — BL-NOVO: Ontology về cái mới và phát kiến cấu kiện lồng nhau

Chương này được hình thành sau Origin Build v0.1.0 khi prior-art audit làm lộ ra một lỗi phân loại phổ biến: **thấy các thành phần đã tồn tại rồi suy ra cấu trúc mới không còn là phát kiến**. BL∞ không chấp nhận phép suy luận đó nếu đối tượng cần đánh giá là một hệ tổ hợp.

## 34.1. Nguyên lý mẹ — BL-NCI

**BL-NCI — Nested Constituent Innovation Principle / Nguyên lý Phát kiến Cấu kiện Lồng nhau.**

Một cấu kiện có thể đồng thời:

1. sử dụng vật liệu/tri thức đã tồn tại;
2. được tái cấu hình để có role mới;
3. là một phát kiến ở cấp cấu kiện;
4. là một bộ phận của phát kiến cấp hệ thống lớn hơn.

Nếu `c` là một component đã biết nhưng trong system `S'` nó nhận cấu trúc hoặc role mới:

\[
c' := (c, Structure_{new}, Role_{new}, Context_{new})
\]

thì việc `c ∈ PriorKnowledge` không tự suy ra `c' ∈ PriorKnowledge`.

Một hệ có thể có cấu trúc đệ quy:

\[
Innovation \supset SubInnovation \supset Mechanism \supset Primitive
\]

và mỗi tầng có thể được định danh, kiểm chứng và audit độc lập.

## 34.2. BL-CNO — Tính mới tổ hợp

Các primitive cũ không làm tổ hợp tất yếu cũ:

\[
c_1,\ldots,c_n\in K_t
\]

không suy ra:

\[
f(c_1,\ldots,c_n)\in K_t
\]

Nếu kết quả chưa thuộc knowledge state tham chiếu, tổ hợp có novelty tại miền đó.

## 34.3. BL-RNO — Tính mới quan hệ

Cho hai graph:

\[
G=(V,E),\qquad G'=(V,E')
\]

Ngay cả khi node set giữ nguyên, nếu:

\[
E'\neq E
\]

thì cấu trúc quan hệ đã khác. Novelty có thể nằm ở edge chứ không cần nằm ở node.

## 34.4. BL-SNO — Tính mới cấu trúc

\[
Components(x)\subseteq K_t
\]

nhưng:

\[
Structure(x)\notin K_t
\]

vẫn có thể tạo một object mới.

## 34.5. BL-ANO — Tính mới kiến trúc

Architectural novelty mạnh hơn việc thêm một edge. Nó xuất hiện khi topology hoặc organization của toàn hệ thay đổi:

\[
Topology(G')\neq Topology(G)
\]

BL-AEGIS được đánh giá chủ yếu ở lớp này, không phải ở câu hỏi từng primitive có tiền thân hay chưa.

## 34.6. BL-FNO — Tính mới chức năng

Nếu, **dưới một system boundary và functional-equivalence criterion được khai báo trước**, tổ hợp thực hiện được chức năng không thuộc union chức năng của các component khi đứng riêng:

\[
F(S)\not\subseteq \bigcup_iF(c_i)
\]

thì hệ là candidate có **functional novelty**. Không được dùng công thức này nếu `function`, `component boundary` hoặc `equivalence` chưa được operationalize đủ rõ.

Đây là tiêu chuẩn quan trọng đối với technology stack: một hệ có thể dùng GitHub, AI, cryptographic hash và open review — đều là công nghệ đã có — nhưng nếu topology mới tạo ra một workflow epistemic chưa tồn tại trong cấu hình tham chiếu, chức năng đó vẫn là đối tượng phát kiến.

## 34.7. BL-PNO — Tính mới quy trình

Output không phải toàn bộ object cần đánh giá. Nếu:

\[
\Gamma_A\neq\Gamma_B
\]

thì một transformation/process mới có thể là phát kiến ngay cả khi output có overlap với output cũ.

## 34.8. BL-ENO — Tính mới nổi sinh

Một property chỉ xuất hiện ở cấp hệ thống có thể được phân loại riêng:

\[
Properties(S)\not\equiv \sum_i Properties(c_i)
\]

BL-ENO không khẳng định mọi tổ hợp đều có emergence; nó cung cấp nhãn khi một property hệ thống không quy giản trực tiếp thành function độc lập của từng component.

## 34.9. BL-IDR — Tính mới suy diễn độc lập

Similarity của output không tự chứng minh similarity của derivation:

\[
Output_A\approx Output_B \not\Rightarrow Path_A=Path_B
\]

Nếu provenance cho thấy các đường sinh khác nhau, ta phải tách ít nhất bốn biến:

\[
Truth,\ Priority,\ Independence,\ ArchitectureOriginality
\]

## 34.10. BL-RDN — Tính mới theo miền tham chiếu

Novelty luôn cần reference domain:

\[
Novel(x\mid K_t,D)
\]

Một object có thể mới với tác giả, mới với discipline, mới với humanity-at-time-t, nhưng không nhất thiết mới tuyệt đối trong mọi miền ontology có thể tồn tại.

Điều này ngăn hai lỗi đối xứng:

- overclaim: “chưa ai trong toàn lịch sử từng nghĩ”; 
- underclaim: “một primitive từng tồn tại nên toàn cấu trúc không mới”.

## 34.11. BL-NTO — Nguyên bản qua biến đổi mới

BL-NTO bác tiêu chuẩn `originality = creation ex nihilo`.

Một formulation tốt hơn:

\[
Originality = NovelTransformation(AbsorbedInformation)
\]

Con người luôn vận hành trên language, culture, observations, tools và social signals đã hấp thụ. Cái được audit là transformation, derivation và resulting structure.

## 34.12. BL-LSI — Ảnh hưởng xã hội tiềm ẩn không đồng nhất phụ thuộc trực tiếp

**BL-LSI — Latent Social Influence Principle.**

Một người có thể hấp thụ tín hiệu phân tán từ xã hội mà không đọc formal source tương ứng. Vì vậy:

\[
EnvironmentalInfluence\neq DirectDependenceOnPriorWork
\]

và:

\[
IndependentDerivation\neq ZeroPriorInfluence
\]

Independent derivation chỉ nên được claim khi provenance hỗ trợ rằng output không được xây trực tiếp bằng cách sao chép/triển khai formal architecture đã biết; nó không đòi một bộ não cách ly khỏi xã hội.

## 34.13. BL-ICR — Quan hệ hội tụ độc lập

BL-ICR là family gồm:

- **BL-ICV — Independent Convergence:** hai đường độc lập hội tụ vào kết quả gần nhau.
- **BL-IRC — Independent Reconstruction:** một cấu trúc được tái dựng độc lập trước khi đối chiếu formal prior work.
- **BL-IGR — Independent Generalization:** derivation độc lập hội tụ một phần rồi phát triển thành formulation rộng hơn.

Các relation này là metadata của provenance; chúng không tự chứng minh priority hay truth.

## 34.14. BL-NVM — Novelty Vector Model

Thay vì câu hỏi nhị phân `mới/không mới`, BL-NVM mô tả:

\[
N(x)=
(N_p,N_r,N_s,N_a,N_f,N_{proc},N_e,N_d)
\]

với:

- `Np`: primitive novelty;
- `Nr`: relational novelty;
- `Ns`: structural novelty;
- `Na`: architectural novelty;
- `Nf`: functional novelty;
- `Nproc`: process novelty;
- `Ne`: emergent novelty;
- `Nd`: derivational novelty.

Các chiều trên **không được giả định trực giao hay độc lập thống kê**. BL-NVM ở v0.2 là ontology/audit vector, chưa phải psychometric scale hoặc measurement instrument đã validated.

Một hệ có thể có `Np` thấp nhưng `Na`, `Nf`, `Nproc` và `Nd` cao. BL-AEGIS hiện được giả thuyết nằm ở profile đó; đây là object cần prior-art audit, không phải kết luận đã chứng minh.

## 34.15. BL-IFH — Innovation Fractal Hierarchy

Phát kiến được mô hình như hierarchy có thể lồng:

\[
Primitive\to Mechanism\to Module\to Subsystem\to Architecture\to MetaSystem
\]

Một node có thể là whole ở cấp dưới và component ở cấp trên.

## 34.16. BL-FCR — Tái phân loại cấu kiện theo chức năng

Nếu một component cũ được gán role mới trong ontology vận hành của system:

\[
Role_{new}(c)\neq Role_{old}(c)
\]

thì system được quyền định nghĩa functional object mới:

\[
c':=(c,Role_{new})
\]

Quyền đặt tên ở đây là quyền định nghĩa object/function trong framework, **không phải quyền sở hữu primitive**.

## 34.17. BL-TNI — Tính mới topology của tích hợp

Nếu cùng một tập component nhưng integration topology tạo feedback loops hoặc capabilities mới:

\[
V_{new}\approx V_{old},\quad Topology_{new}\neq Topology_{old},\quad \exists F_{new}
\]

thì integration itself là một candidate invention.

## 34.18. Quy tắc audit novelty

Prior-art audit phải hỏi tuần tự:

1. primitive nào có tiền thân?
2. relation nào có tiền thân?
3. architecture nào tương đương?
4. function nào tương đương?
5. process nào tương đương?
6. provenance derivation có độc lập không?
7. reference domain của claim “mới” là gì?

**Prior art(component) không tự động là prior art(system).** Ngược lại, nếu tồn tại system trước có cùng topology/function ở mức đủ tương đương, việc đổi tên component không tạo novelty thật.
