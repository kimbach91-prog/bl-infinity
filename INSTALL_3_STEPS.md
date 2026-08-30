# Cài BL∞ v0.2 — bản lười kéo

## Bước 1 — Tạo repo

Trên GitHub tạo **public repository** tên `bl-infinity`, để trống cũng được.

## Bước 2 — Chạy đúng 1 lệnh trong thư mục package đã giải nén

```bash
python scripts/prepare_release.py --github TEN_GITHUB_CUA_MAY --repo bl-infinity --zip
```

Lệnh này tự:

- cài Python dependencies;
- thay username/canonical URL;
- chạy release audit;
- build 68 claim pages + 79 asset pages;
- tạo sitemap/robots/JSON-LD/machine index;
- hash provenance;
- audit lại sau build;
- tạo ZIP configured trong `dist/`.

Nếu Windows không nhận `python`, thử `py` thay cho `python`.

## Bước 3 — Đẩy cả thư mục lên repo, rồi bật 3 thứ

1. `Settings → Pages → Source: GitHub Actions`.
2. `Settings → Features → Discussions`.
3. Trong `Watch` của repo chọn nhận **Discussions** (và bật email trong GitHub notification settings nếu muốn email).

### Comment ngay dưới từng mệnh đề

- Cài giscus cho repo.
- Tạo category `Page Comments` (khuyến nghị kiểu Announcements cho giscus).
- Lấy `repoId` + `categoryId` trên https://giscus.app/vi.
- Điền vào `bl.config.yml`, đổi `comments.enabled: true`, push lại.

### SEO/index pilot

Sau khi site live:

- mở `/robots.txt` và `/sitemap.xml` kiểm tra;
- submit `sitemap.xml` vào Google Search Console nếu verify được property;
- request indexing root + vài Claim URL quan trọng, không spam toàn bộ URL;
- dùng **Claim URL riêng** khi đăng xã hội, ví dụ `/claims/BL-NCI/`;
- không chặn `OAI-SearchBot` nếu muốn có khả năng được ChatGPT Search phát hiện.

Sau đó chạy BL-PIRAL:

`publish → index → reaction → classify → deep audit → patch → version → republish`.
