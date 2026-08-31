# v0.2 Index-Pilot — Preflight Audit Findings

Audit này tách **structural implementation correctness** khỏi **truth of theory**.

## Đã sửa trong v0.2

1. **Claim index quá thô:** v0.1 chỉ có `claims.html`. → Sửa bằng BL-ICO: 68 canonical claim pages + claim-index JSON + sitemap entries.
2. **Asset registry machine chưa đủ:** nhiều BL-* chỉ nằm trong Markdown. → Đồng bộ lên 79 machine assets.
3. **Tên `Semantic Gravity` dễ collision học thuật:** giữ BL-SG như legacy alias, đưa canonical indexing architecture sang **BL-ORBIT**.
4. **Novelty binary gây category error:** thêm BL-NOVO + BL-NVM + reference-domain guardrail.
5. **Nguy cơ overclaim tổ hợp:** mọi novelty claim mới được giữ ở status `proposed/formalizable` trừ phần toán/implementation có thể test trực tiếp.
6. **NVM có nguy cơ bị hiểu là thang đo đã validated:** ghi rõ các dimensions không giả định orthogonal và chưa phải measurement scale.
7. **Functional novelty có nguy cơ mơ hồ:** thêm yêu cầu system boundary + functional equivalence criterion.
8. **Machine JSON trong sitemap có thể làm search landing pages lộn xộn:** bỏ machine endpoints khỏi submitted sitemap; chúng vẫn discoverable từ HTML/llms.txt.
9. **giscus thread có nguy cơ trộn forum và page comments:** default category đổi thành `Page Comments`; forum critique giữ category riêng.
10. **Deploy có thể lỗi sau cấu hình:** thêm `prepare_release.py` chạy configure → release audit → build → hash → audit lại.

## Automated preflight hiện tại

- 68 Claim IDs, không duplicate.
- 79 named assets, không duplicate.
- Không có claim dependency cycle.
- Không có asset dependency cycle.
- Không có unknown dependency trong configured test.
- 155 HTML pages trong configured test.
- 155 canonical URLs, không duplicate.
- 0 broken internal links trong configured test.
- JSON/JSON-LD parse sạch.
- sitemap.xml và feed.xml parse sạch.
- GitHub Actions versions đang khớp ví dụ Pages hiện hành của GitHub ở thời điểm audit.

## Hai trạng thái chưa thể tự động “sửa hộ” trước publish thật

1. **GitHub username / canonical domain** chưa biết nên source package để placeholder. `--release` sẽ cố tình fail cho tới khi `configure.py` hoặc `prepare_release.py` được chạy.
2. **Raw transcript chính xác** chưa được import. Structured reasoning log hiện không được phép masquerade thành byte-for-byte chat export. Đây là provenance warning, không phải logic error.

## Chưa được tuyên bố bởi preflight này

- BL∞ đúng về metaphysics.
- BL-AEGIS là first-in-history tuyệt đối.
- BL-NOVO là taxonomy novelty tối ưu duy nhất.
- social pilot sẽ xác nhận theory.

Các câu trên thuộc Deep Audit / prior-art / empirical phase tiếp theo.
