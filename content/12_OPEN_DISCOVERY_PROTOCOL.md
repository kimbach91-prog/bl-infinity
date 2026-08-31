# 12 — OODP / Giao thức Phát kiến Mở Optimizer

OODP là governance layer suy ra từ vấn đề: chi phí bảo tồn một hypothesis số rất thấp, trong khi chi phí vứt nhầm một phát kiến có thể rất lớn.

## Tách bốn biến

Mỗi công trình I có vector:

\[
I=(T,D,P,O)
\]

- \(T\): truth/validity;
- \(D\): independent derivation;
- \(P\): publication priority;
- \(O\): originality of formulation/framework.

Không cho phép:

\[
P=0\Rightarrow D=0
\]

hay:

\[
PriorArt(component)\Rightarrow PriorArt(framework)
\]

## Preservation-before-validation

\[
Preserve(H)\not\Rightarrow Endorse(H)
\]

Một hypothesis có thể được archive, timestamp, machine-index và phản biện với status `UNVERIFIED`. Điều này giảm false-rejection loss mà không buộc hệ thống phải tin nó.

## Expected epistemic value

Một heuristic phân bổ tài nguyên:

\[
EEV(H)=\frac{P(valid|E)\times Impact\times InformationGain\times Generality}{VerificationCost}
\]

OODP không yêu cầu con số chính xác; nó yêu cầu hệ thống ngừng dùng một biến proxy duy nhất như danh tiếng để quyết định attention.

## Universal publication, earned weight

\[
RightToPublish=Universal
\]

nhưng:

\[
EpistemicWeight=Earned(Evidence,Logic,Reproducibility,AdversarialSurvival)
\]

Đây là nguyên lý chống cả gatekeeping thừa lẫn dân túy tri thức.
