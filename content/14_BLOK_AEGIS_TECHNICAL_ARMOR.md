# 14 — BLOK và BL-AEGIS: lớp giáp kỹ thuật

BLOK là hạ tầng tri thức mở. BL-AEGIS là kiến trúc module bao quanh research object.

## Ranh giới lịch sử

Chương này mô tả chức năng và cấu hình hiện tại, không phải thứ tự sinh thành. Theo current-view đã được Lâm Kim Bách hiệu chỉnh, **hạt nhân nền tảng BLOK có trước chuỗi Optimizer/“Bản chất”**. Việc BLOK được đặt tên, mở rộng và tích hợp vào BL∞ trong Origin Build 2026-08-28 là một mốc formalization/public packaging, không được đánh tráo thành ngày BLOK bắt đầu tồn tại.

BL∞, Optimizer, BLOK và BL-AEGIS giữ identity riêng trong BL-lineage. Quan hệ lịch sử `PRECEDES` không tự biến thành `PARENT_OF`, `DEPENDS_ON`, `IS_PART_OF` hoặc bằng chứng novelty.

## 32 module lõi

1. BL-ASSET — registry tài sản/mệnh đề.
2. BL-CP — cognitive provenance.
3. BL-LOG — reasoning log.
4. BL-CHRONO — timeline/hash lineage.
5. BL-SIGN — chữ ký nguồn gốc.
6. BL-MIRROR — mirror bảo toàn integrity.
7. BL-RELAY — fork/cite/relay có provenance.
8. BL-PCRO — proof-carrying research object.
9. BL-CG — claim–critique graph.
10. BL-MAP — relation map với prior theories.
11. BL-MXF — machine exchange formats.
12. BL-L10N — localization.
13. BL-LC — level-matched critique.
14. BL-EOA — external objection admissibility.
15. BL-MAJ — machine adversarial jury.
16. BL-ARS — adversarial robustness score.
17. BL-RAP — recursive adversarial publishing.
18. BL-OPEN — open challenge.
19. BL-ORB — open research beacon.
20. BL-MGP — machine greeting protocol.
21. BL-CDS — continuous discovery signaling.
22. BL-SG — semantic gravity architecture.
23. BL-IDX — discovery index fabric.
24. BL-AITEST — AI discoverability/interpretion tests.
25. BL-1CLICK — one-click deployment.
26. BLOK-SEED — reusable template.
27. BL-FCL — feedback capture loop.
28. BL-CSC — cognitive supply chain.
29. BL-PV — preservation before validation.
30. BL-TN — tool neutrality.
31. BL-CF — component/framework distinction.
32. BL-ID — independent discovery protocol.

Chỉ việc chọn hoặc không chọn 32 module tạo:

\[
2^{32}-1=4,294,967,295
\]

subset không rỗng. Không phải mọi subset đều hợp lệ; dependency graph và use case quyết định cấu hình có nghĩa.

## 15 cấu hình chuẩn

### Provenance Shield
\[
ASSET+CP+LOG+CHRONO+SIGN
\]

### Argument Armor
\[
PCRO+CG+LC+CF+ID+TN
\]

### Adversarial Reactor
\[
MAJ+EOA+ARS+RAP+OPEN
\]

### Indexing Lance
\[
ORB+MGP+CDS+SG+IDX
\]

### Machine Diplomacy Mesh
\[
MGP+MXF+L10N+AITEST+RELAY
\]

### Distributed Survival Shell
\[
SIGN+MIRROR+RELAY+CDS
\]

### Critique Absorption Field
\[
CG+EOA+FCL+RAP+ASSET
\]

### Noise Deflection Field
\[
LC+EOA+CG+TN+CF
\]

### One-Person Research Lab
\[
CSC+TN+MAJ+MXF+AITEST
\]

### Publication Autopilot
\[
1CLICK+IDX+CDS+MXF+L10N
\]

### Civilian Scholar Kit
\[
SEED+PV+TN+PCRO+1CLICK+FCL
\]

### Independent Discovery Vault
\[
ID+CP+CHRONO+SIGN+MAP
\]

### Semantic Gravity Engine
\[
SG+MAP+IDX+CG+L10N+MXF
\]

### Self-Refining Theory Engine
\[
PCRO+MAJ+ARS+RAP+FCL+CHRONO
\]

### Full Exosuit
\[
BL\text{-}AEGIS_{FULL}=\bigoplus_{i=1}^{32}M_i
\]

## Mục tiêu kỹ thuật

Giáp không “làm claim đúng”. Giáp làm bốn việc:

1. giảm xác suất mất provenance;
2. giảm xác suất phản biện sai tầng được nhầm là refutation;
3. tăng tốc phát hiện lỗi thật;
4. làm research object dễ tìm, dễ máy đọc, dễ fork và dễ audit.
