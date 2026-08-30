# 02 — Định nghĩa và các không gian cơ bản

## Tổng Thực Tại

BL∞ dùng ký hiệu \(\Omega\) cho **Tổng Thực Tại**: miền bao gồm mọi thứ có bất kỳ tư cách tồn tại nào trong ontology đang xét. Đây là một định nghĩa làm việc, không phải bằng chứng rằng con người đã biết cấu trúc của \(\Omega\).

Điểm quan trọng là không tự động đồng nhất:

\[
U_{obs}=\Omega
\]

trong đó \(U_{obs}\) là vũ trụ quan sát được hay mô hình vật lý hiện hành. Equality chỉ được dùng khi có lý do độc lập đủ mạnh.

## Chủ thể nội tại

Một chủ thể \(A\) được gọi là **embedded observer/agent** khi:

\[
A\subseteq\Omega
\]

và mọi phép đo, suy luận, tưởng tượng hay hành động của A đều diễn ra thông qua trạng thái và tương tác nằm trong \(\Omega\).

Điều này không khiến A “biết” \(\Omega\). Nó chỉ khiến hoạt động nhận thức của A là một phần của cái A đang cố nhận thức.

## Biểu diễn

Một representation \(r\) là trạng thái/cấu trúc mà A sử dụng để mang nội dung về một đối tượng, mô hình, tưởng tượng hoặc khả năng.

Nếu A thực sự sinh \(r\), ta có một sự kiện nội tại:

\[
Generate_A(r)\Rightarrow r\in\Omega
\]

Nếu \(r\) biểu diễn một con chó 700 đầu, kết luận trực tiếp chỉ là **representation đó đã tồn tại như một trạng thái của hệ**. Không được tự động suy ra con chó 700 đầu đã actualize độc lập.

## Actual, reachable, constructible

Một trạng thái \(h\) là **actual** tại thời điểm \(t\) nếu nó đang được hiện thực hóa trong miền đang xét.

Một trạng thái \(h\) là **reachable** từ \(x_0\) dưới repertoire \(U\) nếu tồn tại một chuỗi biến đổi hợp lệ:

\[
T_n(\dots T_2(T_1(x_0)))=h,\qquad T_i\in U
\]

Một target có thể chưa actual nhưng reachable. Ngược lại, một target được mô tả rõ chưa chắc reachable dưới luật và nguồn lực hiện tại.

**Constructible** nhấn mạnh tồn tại một constructor/quy trình có thể thực hiện transformation với độ tin cậy yêu cầu. BL∞ dùng khái niệm này như một cầu nối từ imagination tới kỹ thuật nhưng không đồng nhất nó với mere conceivability.

## Không gian khả niệm

\(\mathcal C_A\) là tập các object description/representation mà agent A có thể sinh bằng primitive, operator, ngôn ngữ, bộ nhớ và compute của nó.

Nếu primitive set là \(P_A\) và operator set là \(F_A\), có thể mô hình hóa sơ bộ:

\[
\mathcal C_A=Closure_{F_A}(P_A)
\]

Đây chỉ là abstraction; cognition thực không nhất thiết đóng dưới một formal algebra đơn giản.

## Không gian khả đạt mở rộng

Repertoire kỹ thuật của A có thể thay đổi:

\[
U_{t+1}=U_t\cup NewTools(U_t,\mathcal C_A,E_t)
\]

khi đó:

\[
Reach(x,U_t)\subseteq Reach(x,U_{t+1})
\]

nếu các năng lực cũ được bảo toàn. Điều này tạo khái niệm **recursive capability expansion**: một tool giúp xây tool tiếp theo, làm reachable space thay đổi theo thời gian.

## Phân biệt quan trọng

BL∞ khóa các bất đẳng thức khái niệm sau:

\[
Representation(x)\neq Referent(x)
\]

\[
NotActual(x)\not\Rightarrow Impossible(x)
\]

\[
Conceivable(x)\not\Rightarrow PhysicallyReachable(x)
\]

\[
Inconceivable_A(x)\not\Rightarrow Impossible_\Omega(x)
\]

\[
Observed_A\not\equiv TotalReality
\]

Những distinction này là “khớp giáp” chống các phản bác sai tầng và cũng chống chính BL∞ tự phóng đại claim của nó.
