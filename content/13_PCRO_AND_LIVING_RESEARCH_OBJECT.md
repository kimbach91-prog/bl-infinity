# 13 — BL-PCRO: Proof-Carrying Research Object

Một paper truyền thống thường là một snapshot. BL-PCRO coi một công trình là object sống có cấu trúc kiểm tra được.

\[
R=(C,P,D,E,V,K,H,S)
\]

- C — claims;
- P — premises;
- D — derivations;
- E — evidence;
- V — provenance;
- K — critiques;
- H — history/version lineage;
- S — signatures/hashes.

## Claim graph

Mỗi claim có ID và dependency:

\[
G_C=(V_C,E_C)
\]

Nếu `BL-P-010` phụ thuộc `BL-A-001` và `BL-D-004`, một challenge vào dependency phải propagate tới downstream claims.

## Trạng thái claim

Mỗi node có thể ở:

- proposed;
- formalized;
- supported;
- contested;
- revised;
- rejected;
- superseded;
- conditional;
- speculative.

Không có binary “paper accepted = tất cả claim đúng”.

## Publication as process

\[
PCRO_0\to Attack\to PCRO_1\to NewEvidence\to PCRO_2
\]

Mỗi version giữ hash, timestamp và changelog. Critique được credit bằng Critique ID nếu góp phần thay đổi claim.
