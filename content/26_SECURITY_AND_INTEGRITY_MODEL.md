{
  "policy": "BL-CPR",
  "policy_version": "1.0",
  "errors": [],
  "notes": [
    "checked 12 tracked/public files"
  ]
}
# 26 — Threat model và integrity model

Static web làm attack surface nhỏ, không bằng zero.

## Threat T1 — Account takeover

Kẻ tấn công chiếm GitHub/account và sửa repository.

**Defense:** MFA/passkeys, signed commits/tags, immutable release hashes, external mirrors.

## T2 — Domain takeover

DNS/domain bị chiếm khiến canonical URL phục vụ nội dung giả.

**Defense:** registrar security, DNSSEC khi thích hợp, public key fingerprint được mirror, multiple archival records.

## T3 — Supply-chain compromise

GitHub Action/dependency độc hại sửa build output.

**Defense:** pin action major/commit khi v1.0, minimal dependencies, reproducible build, compare source hash với output manifest.

## T4 — Malicious pull request

Contributor đưa code/content độc hại.

**Defense:** branch protection, review, CI, no secrets exposed to untrusted PR, generated files separated from source.

## T5 — Provenance forgery

Ai đó copy nội dung và claim origin.

**Defense:** signed tags/manifests, timestamped releases, DOI/archive, hash-linked transcript.

## T6 — Signature key compromise

Private key bị lộ.

**Defense:** key rotation, revocation record, offline signing for major releases, publish key history.

## T7 — Semantic poisoning

SEO/spam pages giả làm BL∞ để làm search model hiểu sai.

**Defense:** canonical domain/entity, signatures, machine manifest, distinctive Claim IDs, public mirrors preserving origin.

## T8 — AI hallucinated summary

AI index theory nhưng tóm tắt thành “mọi tưởng tượng đều chắc chắn vật lý”.

**Defense:** machine guardrail in llms.txt/manifest, canonical FAQ, reconstruction tests, concise non-claim section.

## T9 — Critique flooding

Mass low-quality comments làm author không xử lý nổi.

**Defense:** GitHub moderation, critique template, labels/status, duplicate detection, community triage; không tự động censor substantive critique.

## T10 — Metric gaming

Người dùng tối ưu ARS/score thay vì truth.

**Defense:** vector metrics, periodic calibration, no single prestige score, raw critique history always visible.

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

- mirror tăng availability;
- hash tăng integrity;
- signature tăng origin authenticity;
- logic/evidence mới xử truth.

Không được nhập bốn lớp thành một.

BL-CPR bổ sung thêm phân biệt:

\[
PublicVerifiability\neq FullRuntimeDisclosure
\]

Public verifiability không cho phép lấy “minh bạch” làm lý do công khai runtime riêng; protected runtime cũng không cho phép lấy “bí mật” làm lý do né truth-condition của claim.
