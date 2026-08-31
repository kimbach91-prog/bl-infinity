# 27 — Metrics: đo mà không biến thành Goodhart machine

Origin build không dùng một “điểm chân lý”. Nó dùng vector diagnostics.

## Claim Quality Vector

\[
Q_C=(Cl,Ty,Sc,De,Ev,Re,Pr)
\]

- Cl — clarity;
- Ty — correct type labeling;
- Sc — scope discipline;
- De — derivation completeness;
- Ev — evidence strength where relevant;
- Re — reproducibility/checkability;
- Pr — provenance quality.

## Critique Quality Vector

\[
Q_R=(Ta,Sp,St,Ch,Ev,Ac)
\]

- Ta — target precision;
- Sp — specificity;
- St — logical strength;
- Ch — checkability;
- Ev — evidence/countermodel;
- Ac — actionable correction value.

## Adversarial history

Không đếm “bao nhiêu AI đồng ý”. Ghi:

- number of distinct attack classes;
- open critical findings;
- resolved major findings;
- independent reproductions;
- alternate proofs;
- unresolved prior-art identity questions.

## Revision quality

\[
RQ=\frac{ResolvedValidFindings\times SeverityWeight}{RevisionCost+NewErrorsIntroduced}
\]

Chỉ là heuristic; không publish như universal metric khi chưa calibration.

## Discovery preservation metrics

- time-to-registration;
- cost-to-register;
- percentage with provenance complete;
- percentage later independently rediscovered;
- false-rejection candidates recovered;
- attention cost per valid finding.

## Goodhart guardrail

Khi metric trở thành target, behavior có thể tối ưu metric thay vì underlying value. Vì vậy:

1. giữ raw evidence;
2. rotate/audit metrics;
3. không trao quyền tuyệt đối cho scalar score;
4. cho critique chính metric;
5. công khai formula/version.
