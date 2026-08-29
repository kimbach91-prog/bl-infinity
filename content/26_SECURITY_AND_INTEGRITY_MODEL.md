# 26 — Threat model và integrity model

Static web làm attack surface nhỏ, không bằng zero.

## T1–T4 — Hạ tầng và chuỗi cung ứng

- **Account/domain takeover:** dùng MFA, signed tags, immutable hashes, registrar security và mirror.
- **Supply-chain compromise:** pin action, tối thiểu dependency, reproducible build, đối chiếu source/output hash.
- **Malicious pull request:** branch protection, review, CI, không cấp secret cho untrusted PR.

## T5–T8 — Provenance và diễn giải

- **Provenance forgery:** signed manifests, timestamped releases, DOI/archive, hash-linked source.
- **Signature key compromise:** rotation, revocation record, offline signing cho major release.
- **Semantic poisoning:** canonical entity/domain, distinctive Claim IDs, public mirrors.
- **AI hallucinated summary:** machine guardrail, FAQ, reconstruction test, non-claim boundary.

## T9–T10 — Governance

- **Critique flooding:** template, labels/status, duplicate detection, community triage; không censor phản biện có nội dung.
- **Metric gaming:** vector metrics, calibration định kỳ, không dùng một prestige score, giữ raw critique history.

## T11 — Runtime exfiltration

Public repo vô tình chứa prompt vận hành hoàn chỉnh, routing weights, private diagnostics, credential, corpus riêng, raw private conversation hoặc exploit chưa vá.

**Defense:** BL-CPR classification trước commit; `.gitignore` cho private paths; `scripts/disclosure_audit.py` chặn secret/key material và forbidden paths; review riêng cho mọi thay đổi `machine/`, `scripts/`, `provenance/`; không dùng “minh bạch” để biện minh cho việc xuất dữ liệu riêng.

## T12 — Secrecy as epistemic escape

Ngược lại, nhãn “runtime riêng” bị dùng để giấu tiền đề, bằng chứng bất lợi, điều kiện bác bỏ hoặc thay đổi claim.

**Defense:** mọi yếu tố quyết định truth-status của claim công khai vẫn phải public; phần giữ riêng chỉ được bảo vệ lợi thế thực thi, quyền riêng tư hoặc an toàn, không được tạo miễn nhiễm phản biện.

## Integrity principle

\[
Availability\neq Integrity\neq Authenticity\neq Truth
\]

Mirror tăng availability; hash tăng integrity; signature tăng origin authenticity; logic/evidence mới xử truth. BL-CPR thêm phân biệt:

\[
PublicVerifiability\neq FullRuntimeDisclosure
\]

Không được nhập các lớp này thành một.

