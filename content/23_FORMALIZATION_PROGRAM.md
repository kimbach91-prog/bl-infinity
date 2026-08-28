# 23 — Chương trình formalization toán học

Mục tiêu của chương này không phải “trang trí công thức”, mà chỉ ra với từng phần BL∞: object nào, relation nào, theorem nào có thể formalize và chỗ nào chưa được quyền gọi là chứng minh.

## 1. State-space skeleton

Một system được mô hình hóa tối thiểu bởi:

\[
\mathcal S=(X,U,T,O)
\]

trong đó:

- \(X\) là state space;
- \(U\) là tập action/transformation admissible;
- \(T:X\times U\to X\) là transition relation/function, hoặc stochastic kernel nếu dynamics ngẫu nhiên;
- \(O:X\to Y_A\) là observation map của agent A.

Nếu dynamics không deterministic, thay \(T\) bằng relation hoặc kernel:

\[
K(x'|x,u)
\]

BL∞ cần tránh giả định một formalism duy nhất mô tả mọi ontology. Skeleton này là model-class ban đầu để kiểm tra reachability và observer limitation.

## 2. Embedded observer

Cho \(A\) là subsystem có state space \(X_A\subseteq X\). Observation map:

\[
O_A:X\to Y_A
\]

Nếu:

\[
\exists x_1\neq x_2:O_A(x_1)=O_A(x_2)
\]

thì A không thể distinguish hai state chỉ bằng observation output đó. Nếu global-model mapping có cùng property, ta có underdetermination ở cấp model.

### Target theorem family

**Observer Non-Injectivity Theorem:** xác định điều kiện resource/sensor/computation khiến \(O_A\) tất yếu non-injective.

Đây sẽ là chỗ cần kết nối information theory, observability trong control theory và formal epistemology.

## 3. Representation map

Cho:

\[
R_A:X_A\to \mathcal D_A
\]

là mapping từ neural/computational/internal states tới descriptions/representations. Nếu một representation được instantiate, ta có state vật lý/thông tin của A. Nội dung referential được mô hình hóa bởi interpretation function:

\[
I_A:\mathcal D_A\to \mathcal P(X)\cup\mathcal M
\]

trong đó \(\mathcal M\) có thể chứa model/intensional objects. Điều này giữ riêng **token representation** và **extension/referent**.

## 4. Conceivability space

Một abstraction generative:

\[
\mathcal C_A=Closure_{F_A}(P_A)
\]

với primitive vocabulary \(P_A\), operators \(F_A\), resource bounds \(B_A\). Phiên bản resource-bounded:

\[
\mathcal C_A(B)=\{d\in Closure_{F_A}(P_A):Cost_A(d)\le B\}
\]

Điều này cho phép nghiên cứu tăng compute/tools làm \(\mathcal C_A\) thay đổi.

## 5. Reachability

Với transition relation \(T\), reachable set sau không quá n bước:

\[
Reach_n(x_0)=\{x_n:\exists u_1,...,u_n\ T(...T(x_0,u_1),...,u_n)=x_n\}
\]

Toàn finite reachable closure:

\[
Reach^*(x_0)=\bigcup_{n\ge0}Reach_n(x_0)
\]

Resource-constrained reachability:

\[
Reach_{B}(x_0)=\{x: \exists \pi,\ Cost(\pi)\le B,\ \pi(x_0)=x\}
\]

## 6. Recursive capability

Cho tool repertoire \(U_t\). Một meta-constructor \(G\) sinh tool mới:

\[
U_{t+1}=U_t\cup G(U_t,K_t,R_t)
\]

Nếu \(U_t\subseteq U_{t+1}\) và transition semantics giữ lại toàn action cũ:

\[
Reach(x,U_t)\subseteq Reach(x,U_{t+1})
\]

Đây có thể formalize như monotonicity theorem dưới assumptions cụ thể.

## 7. Reachability–conceivability gap

Các tập cần nghiên cứu:

\[
G_{RC}=\mathcal R-\mathcal C_A
\]

\[
G_{CR}=\mathcal C_A-\mathcal R
\]

\[
I_{RC}=\mathcal R\cap\mathcal C_A
\]

Một strong result cho BL∞ sẽ là chứng minh \(G_{RC}\neq\varnothing\) trong một class hệ hữu hạn observer + larger generative environment. Ví dụ có thể dùng uncomputable states/functions, description complexity, diagonalization hoặc resource-bounded agents; nhưng mọi bridge sang physical reality phải được tách.

## 8. Description complexity

Nếu descriptions finite strings trên alphabet hữu hạn:

\[
|\Sigma^*|=\aleph_0
\]

Nếu state set \(X\) uncountable, không tồn tại injection từ X vào finite-string descriptions nếu mỗi state đòi unique finite string.

Có thể bổ sung Kolmogorov complexity:

\[
K(x)=\min_{p:U(p)=x}|p|
\]

nhưng phải cực cẩn thận: uncomputability của K và dependence on universal machine up to additive constant không được che giấu.

## 9. Observation filter as stochastic selection

Cho source distribution \(P_\Omega(x)\) và selection function \(s_A(x)\in[0,1]\):

\[
P_A(x|observed)=\frac{s_A(x)P_\Omega(x)}{\int s_A(z)P_\Omega(z)dz}
\]

khi normalization hữu hạn. Nếu \(s_A\) không constant, observed distribution có thể bị bias.

Đây là một formal bridge tốt cho BL-OFB.

## 10. Plenitude extension

BL-A005 phải được viết như axiom schema:

\[
\forall h\in\mathcal H_L, Cons_L(h)\Rightarrow\exists W\in\Omega:W\models_L h
\]

Questions:

- \(\mathcal H_L\) là set hay proper class?
- Consistency syntactic hay satisfiability semantic?
- logic L nào?
- W “tồn tại” theo mode nào?
- duplicate/isomorphic models được đếm ra sao?
- measure trên ensemble là gì?

Nếu không trả lời, Plenitude chỉ là metaphysical slogan.

## 11. Critique graph formalization

Claim graph:

\[
G_C=(V,E_d,E_a)
\]

- \(E_d\): dependency edges;
- \(E_a\): attack/support edges.

Một finding phá node \(v\) có impact set:

\[
Impact(v)=Descendants_{E_d}(v)
\]

nhưng downstream claim chỉ tự động fail nếu dependency là logically necessary và không có alternate proof path.

## 12. Provenance graph

Artifact graph:

\[
G_P=(Artifacts,DerivedFrom,SignedBy,TimestampedAt,Transforms)
\]

Integrity root:

\[
H_{root}=MerkleRoot(H(file_1),...,H(file_n))
\]

Origin build dùng linear hash manifest đơn giản; public v1.0 có thể chuyển sang Merkle tree.

## 13. Adversarial score

Không coi score là truth probability nếu chưa calibration. Có thể bắt đầu như vector:

\[
ARS(R)=(L,M,E,P,S,V)
\]

với logic integrity, mathematical check, evidence, provenance, scope discipline, adversarial survival. Chỉ sau empirical calibration mới nén thành scalar.

## 14. Tối ưu nguồn lực nghiên cứu

Một formulation decision-theoretic:

\[
EEV(H)=\frac{P(valid|E)\cdot V_{impact}\cdot IG(H)}{C_{verify}+C_{opportunity}}
\]

False-rejection loss:

\[
L_{FR}=P(valid|E)\cdot V_{lost}\cdot P(irrevocable|discard)
\]

Preservation có lợi khi storage/preservation cost thấp hơn expected discard loss, nhưng spam/attention cost phải được đưa vào model.

## 15. Formalization priority

Thứ tự nên làm:

1. exact definitions;
2. embedded observer theorem;
3. reachability/capability monotonicity;
4. description-space theorem;
5. observation-filter probability model;
6. claim graph semantics;
7. provenance integrity;
8. only then attempt stronger metaphysical bridge.

Nếu làm ngược, BL∞ dễ có quá nhiều ký hiệu nhưng thiếu theorem thực.
