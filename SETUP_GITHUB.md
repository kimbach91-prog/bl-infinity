# Cài đặt BL∞ lên GitHub — bản tối giản

Mục tiêu: **một repo public + GitHub Pages + Discussions + giscus + Actions**.

## 1. Tạo repository

Tên đề xuất: `bl-infinity`.

Upload **toàn bộ nội dung bên trong package này** vào root repository, không upload nguyên thư mục cha khiến repo bị lồng thêm một cấp.

Branch mặc định: `main`.

## 2. Cấu hình một lần

Cách ít lỗi nhất:

```bash
python -m pip install PyYAML
python scripts/configure.py --github TEN_GITHUB_CUA_BAN --repo bl-infinity
```

Nếu không truyền `--url`, script dùng `https://TEN_GITHUB_CUA_BAN.github.io/bl-infinity/`. Nếu có domain riêng:

```bash
python scripts/configure.py --github TEN_GITHUB_CUA_BAN --repo bl-infinity --url https://domain-cua-ban.example/bl-infinity/
```

Có thể sửa `bl.config.yml` thủ công, nhưng khi đó nhớ sửa cả metadata repo/citation liên quan.

## 3. Bật GitHub Pages

Repository → **Settings → Pages**.

Chọn source/deployment bằng **GitHub Actions**. Workflow `.github/workflows/pages.yml` đã được đóng gói.

Mỗi push vào `main` sẽ:

1. checkout;
2. cài dependencies;
3. chạy `scripts/audit.py`;
4. build static site;
5. deploy Pages.

## 4. Bật Discussions

Repository → **Settings → General/Features → Discussions**.

Tạo category gợi ý:

- `Page Comments` — nên dùng category kiểu **Announcements** riêng cho giscus để comment theo từng URL không trộn với forum mở.
- `Formal Critiques`
- `Mathematical Objections`
- `Prior Art`
- `Extensions`
- `Independent Discoveries`
- `AI Reviews`
- `General`

Theo dõi repository/Discussions bằng GitHub notifications hoặc email để tác giả nhận phản hồi.

## 5. Bật giscus để comment ngay trên website

1. Cài GitHub App **giscus** cho repo.
2. Repo phải public và Discussions đã bật.
3. Vào cấu hình giscus, chọn repo và category `Page Comments`. giscus hiện khuyến nghị category kiểu Announcements cho comment-mapping để discussion mới do maintainer/giscus tạo, trong khi các category phản biện mở vẫn tách riêng.
4. Lấy `repoId` và `categoryId`.
5. Sửa `bl.config.yml`:

```yaml
comments:
  enabled: true
  repo: "USERNAME/bl-infinity"
  repo_id: "..."
  category: "Page Comments"
  category_id: "..."
  mapping: "pathname"
```

6. Push lại. Comment box sẽ xuất hiện cuối các trang.

## 6. Notification flow

Website comment → giscus → GitHub Discussion → GitHub notification/email → tác giả trả lời.

Nếu critique tìm ra lỗi cần hành động:

Discussion → Issue → Pull Request → phiên bản mới.

## 7. Release đầu tiên

Sau khi kiểm tra:

- tạo tag `v0.2.0-index-pilot`;
- tạo GitHub Release;
- đính ZIP/source snapshot nếu muốn;
- sau khi có exact raw transcript, tạo release provenance riêng.

## 8. Custom domain — tùy chọn nhưng nên làm

Khi có domain riêng:

- cấu hình custom domain trong Pages hoặc đưa site qua Cloudflare;
- sửa `canonical_url`;
- kiểm tra HTTPS;
- tránh tồn tại nhiều canonical origins không redirect/không canonicalize.

## 9. Điều không cần làm

- Không cần database.
- Không cần server PHP/Node chạy 24/7.
- Không cần comment backend riêng.
- Không cần hidden SEO text.
- Không cần crawler backdoor.

Static site + GitHub/Discussions đã đủ cho index pilot v0.2.


## 10. Vòng thử đầu tiên — BL-PIRAL

Sau khi site live:

1. mở `/claims/BL-NCI/` hoặc claim pilot khác;
2. copy canonical URL để đăng mạng xã hội;
3. mọi phản biện nên trỏ đúng Claim ID;
4. giscus/Discussions giữ reaction theo URL;
5. critique đủ mạnh → tạo Issue `Deep Audit Finding`;
6. patch claim/content → tăng version → push;
7. giữ release cũ để provenance không bị rewrite.

Đừng phát hàng nghìn mệnh đề ở vòng đầu. Chọn vài chục claim để đo BL-SRS và tìm lỗi hạ tầng trước.


## 11. Official references đã kiểm lại ở v0.2

- GitHub Pages publishing source / Actions: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- GitHub Pages automatic deploy example: https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically
- GitHub Discussions quickstart: https://docs.github.com/en/discussions/quickstart
- giscus configuration: https://giscus.app/vi
- OpenAI publisher/search crawler FAQ: https://help.openai.com/en/articles/12627856-publishers-and-developers-faq
- Google canonicalization: https://developers.google.com/search/docs/crawling-indexing/canonicalization

Các external UI có thể đổi theo thời gian; logic repo không phụ thuộc wording chính xác của nút.
