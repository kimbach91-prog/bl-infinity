# 26 — Threat model và integrity model

Static web làm attack surface nhỏ, không bằng zero. BL∞ vì vậy dùng **defense in depth + fail-closed release**: nhiều lớp độc lập cùng bảo vệ account, repository, supply chain, build, disclosure, browser, provenance, translation và recovery. Không coi một lớp mạnh là lý do bỏ các lớp còn lại.

## 26.1. Nguyên tắc không nhập nhằng

\[
Availability\neq Integrity\neq Authenticity\neq Truth
\]

- mirror tăng availability;
- hash tăng integrity;
- signature tăng origin authenticity;
- logic/evidence mới xử truth.

BL-CPR bổ sung:

\[
PublicVerifiability\neq FullRuntimeDisclosure
\]

Public verifiability không cho phép lấy “minh bạch” làm lý do công khai runtime riêng; protected runtime cũng không cho phép lấy “bí mật” làm lý do né truth-condition của claim.

## 26.2. Mười lớp bảo mật công khai

### L0 — Account & Authority

Phishing-resistant MFA/passkeys, recovery hygiene, minimal admin authority, không dùng shared credential. Đây là platform/owner control; repository code không được giả vờ rằng nó tự enforce được.

### L1 — Repository Governance

Default branch cần được bảo vệ bằng ruleset/branch protection, review trước merge và required CI. Generated `site/` không được coi là source. Release quan trọng nên có signed tag/attestation khi hạ tầng ký phù hợp.

**Current security boundary:** nếu GitHub ruleset chưa được bật thì phải ghi nhận là open gap, không dùng CI prose để giả rằng branch đã protected.

### L2 — Supply Chain & CI

- GitHub Actions pin bằng **full commit SHA**, không dùng floating tag làm release authority;
- workflow/job dùng least privilege;
- checkout `persist-credentials: false`;
- dependency trực tiếp pin exact version;
- `pip-audit` kiểm dependency;
- Dependabot theo dõi `pip` và `github-actions`;
- PR build không nhận quyền deploy Pages.

### L3 — Publication & Disclosure

BL-CPR P0–P3, forbidden-path scan, secret/key scan, public allowlist, protected-runtime exclusion và machine projection minimization. Mọi thứ commit vào public repo được xem là public dù không nằm trong sitemap/navigation.

### L4 — Build & Rendering

Markdown raw HTML phải bị escape trước khi render. Build tạo lại `site/` từ clean tree. Security audit chặn inline event handler, `javascript:`/`data:text/html` URL và active-script semantics không được allowlist.

### L5 — Browser & Client Policy

Static page dùng Content Security Policy ở mức host cho phép, strict referrer policy, HTTPS upgrade, local assets và chỉ mở origin bên ngoài tối thiểu cần thiết cho giscus.

**Giới hạn phải nói thật:** GitHub Pages không cho repository tự đặt mọi HTTP response header. Các control chỉ có hiệu lực khi browser hỗ trợ CSP qua meta. Header-only policy như server `frame-ancestors`, HSTS tuning hoặc Permissions-Policy cần reverse proxy/CDN hoặc host khác nếu về sau được triển khai.

### L6 — Integrity & Provenance

Content hash, Claim ID, version, provenance graph, translation source hash và translation hash. Hash chứng minh quan hệ byte, không chứng minh claim đúng.

### L7 — Recovery & Incident Response

Credential compromise ưu tiên revoke/rotate trước. Exposure cần preserve evidence riêng, purge active tree/history khi cần, rebuild Pages/discovery/mirror và yêu cầu provider purge nếu byte-level eradication cần thiết. Mọi incident material phải tạo regression test.

### L8 — Maintenance & Evolution

Audit chạy mỗi pull request và scheduled weekly. Dependency/Action update được Dependabot kiểm tra. Threat model review theo tháng hoặc ngay khi hosting, dependency, identity, disclosure boundary hay build topology đổi materially.

### L9 — Translation Integrity

Bản EN là derivative representation, không phải independent theory version. Phải giữ source version/file set, source hash, translation hash, translator/model class, review status và coverage. Translation không được tự đổi authorship, chronology, truth-state hay evidential strength. Khi wording material khác nhau và bản EN chưa review, full Vietnamese public source là authority của current wording.

## 26.3. Threat registry

### T1 — Account takeover

Kẻ tấn công chiếm GitHub/account và sửa repository.

**Defense:** passkeys/MFA, hardened recovery, minimal admin, signed releases, external mirrors.

### T2 — Domain/hosting takeover

Canonical URL hoặc deployment path phục vụ nội dung giả.

**Defense:** HTTPS, host account security, canonical entity, external mirrors, public fingerprints/hashes. Nếu dùng custom domain sau này: registrar hardening + DNSSEC khi phù hợp.

### T3 — Supply-chain compromise

Action/dependency độc hại sửa build output.

**Defense:** full-SHA Action pins, exact direct dependencies, pip-audit, Dependabot, least privilege, review dependency delta.

### T4 — Malicious pull request

Contributor đưa code/content độc hại.

**Defense:** protected branch target, review, CI, không cấp deploy permission cho PR build, raw HTML escaping, source-generated-output separation.

### T5 — Provenance forgery

Ai đó copy nội dung và claim origin.

**Defense:** versioned public sources, Claim IDs, manifests/hashes, signed tag/attestation khi khả dụng, archive/mirror và historical graph.

### T6 — Signing-key compromise

Private key bị lộ.

**Defense:** key rotation/revocation, offline/hardware-backed signing cho release quan trọng khi triển khai, publish key history; private key tuyệt đối không nằm trong repo public.

### T7 — Semantic poisoning

SEO/spam/clone làm search model hiểu sai BL∞.

**Defense:** canonical URL/entity, Claim IDs, machine manifest, non-claim section, provenance, reconstruction tests, multiple public discovery surfaces.

### T8 — AI hallucinated summary

AI index theory nhưng nâng conjecture thành fact hoặc nén sai boundary.

**Defense:** llms.txt/manifest, canonical FAQ/non-claims, Claim Registry, translation status, reconstruction audit.

### T9 — Critique flooding

Mass low-quality comment làm author không xử lý nổi.

**Defense:** moderation, critique template, Claim ID, duplicate detection, community triage; không dùng anti-spam để tự động censor substantive critique.

### T10 — Metric gaming

Người dùng tối ưu score thay vì truth.

**Defense:** vector metrics, calibration, no single prestige score, raw critique history và Reality Veto.

### T11 — Runtime exfiltration

Public repo vô tình chứa production prompt, routing weights, private diagnostics, credential, private corpus, raw conversation hoặc exploit chưa vá.

**Defense:** BL-CPR classification trước commit; `.gitignore`; `scripts/disclosure_audit.py`; security audit; public allowlist; no full runtime disclosure.

### T12 — Secrecy as epistemic escape

Nhãn “runtime riêng” bị dùng để giấu premise, adverse evidence, falsifier hay claim change.

**Defense:** mọi yếu tố quyết định public truth-status vẫn phải public hoặc claim phải bị narrow/hold.

### T13 — Translation drift

Bản dịch đổi nghĩa, tăng độ chắc, đổi scope hoặc làm người đọc tưởng bản rút gọn là full translation.

**Defense:** translation index, paired hreflang, source/target hashes, explicit coverage, review state, no silent truth-state promotion.

### T14 — Floating CI reference

Action tag bị move hoặc compromise khiến build chạy code khác mà repo không đổi.

**Defense:** pin full commit SHA; Dependabot cập nhật SHA qua PR để thay đổi luôn visible/auditable.

### T15 — Stale vulnerable dependency

Build dependency cũ có vulnerability đã biết.

**Defense:** pip-audit, Dependabot, exact direct pins, weekly scan, rollback nếu update phá build.

### T16 — Static-host header gap

Security design viết ra header mà GitHub Pages không thực sự gửi, tạo false security.

**Defense:** phân biệt meta-deliverable CSP với header-only controls; audit không được đánh dấu header-only control ACTIVE nếu host không support; chỉ nâng state sau khi reverse proxy/CDN readback xác nhận.

## 26.4. Release law

Một release chỉ được public khi đồng thời qua:

`Epistemic audit → Disclosure audit → Security audit → Build → Post-build security audit → Deploy`

Nếu bất kỳ gate nào fail: **không deploy**. Nếu check tạo false positive lặp lại, sửa/calibrate check có causal log; không vô hiệu hóa lớp chỉ để pipeline xanh.

## 26.5. Maintenance law

Bảo mật không phải “cài một lần”. Mỗi vòng maintenance phải kiểm ít nhất:

- dependency/action drift;
- secret/disclosure regression;
- translation drift;
- unsafe renderer/client change;
- new external origin;
- current hosting limitations;
- incident/negative knowledge mới;
- control nào đang tồn tại trên giấy nhưng không được readback thực tế.

Mục tiêu là giảm attack surface và correction latency theo thời gian, không phải tích càng nhiều security vocabulary càng tốt.
