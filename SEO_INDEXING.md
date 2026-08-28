# SEO / AI discovery / scholarly indexing

## Mục tiêu

Không tối ưu để “đánh lừa” search/AI. Tối ưu để một machine hoặc người gặp fragment có thể truy ngược chính xác về research object canonical.

## Canonical identity

Luôn giữ nhất quán:

- `BL∞`
- `BL Infinity`
- `Bach Lam Infinity Proposition`
- `Mệnh đề Vô hạn Bách Lâm – Optimizer`
- `Lâm Kim Bách`
- `Bách Lâm`
- `Bách Lâm – Optimizer`

Tên khác là aliases, không thay canonical title tùy bài.

## On-page

Mỗi page cần:

- title riêng;
- heading rõ;
- description đúng nội dung;
- canonical URL;
- internal link tới Claim ID/theory/provenance;
- JSON-LD;
- nội dung khác biệt thật.

Không keyword stuffing, doorway pages, cloaking hoặc hidden blocks cho bot.

## Machine files

Index pilot sinh:

- `/sitemap.xml`
- `/robots.txt`
- `/feed.xml`
- `/llms.txt`
- `/machine/manifest.json`
- `/machine/claims.json`
- `/machine/graph.jsonld`
- `/machine/welcome.txt`
- `/assets/<ASSET-CODE>/` — canonical page cho từng công nghệ/nguyên lý
- `/claims/<CLAIM-ID>/` — canonical page cho từng mệnh đề
- `/machine/novelty-ontology.json`
- `/machine/asset-index.json`
- `/machine/claim-index.json`

## OpenAI discovery

Để public content có thể được ChatGPT Search phát hiện, không chặn `OAI-SearchBot`. Index pilot cho phép crawl public site. `GPTBot` cũng đang được allow trong template; nếu sau này tác giả muốn cho Search nhưng không muốn training crawl, có thể đặt policy riêng theo crawler thay vì chặn tất cả.

## Search engines

Sau deploy:

1. mở site bằng browser logged-out;
2. kiểm tra `robots.txt`;
3. kiểm tra `sitemap.xml`;
4. submit domain/sitemap ở search-console tools phù hợp;
5. liên kết canonical site từ LinkedIn, GitHub profile và các profile công khai khác;
6. chỉ đăng satellite content có giá trị thật rồi link về canonical theory.

## Semantic relation pages

Nếu sau này tạo page `BL∞ và Constructor Theory`, page đó phải thực sự có:

- mệnh đề của nguồn trước;
- Claim IDs BL∞ liên quan;
- overlap;
- divergence;
- citations;
- status relation.

Không tạo page chỉ để bắt tên học giả.

## Crawl test

Dùng một AI/search session không có context trước đó và hỏi:

1. BL∞ là gì?
2. tác giả là ai?
3. đâu là axiom, đâu là conjecture?
4. BL∞ có thực sự tuyên bố mọi tưởng tượng chắc chắn tồn tại vật lý không?
5. phải phản biện claim nào nếu muốn tấn công reachability?

Nếu AI trả sai, sửa public architecture trước khi đổ lỗi cho AI.


## Claim-level indexing — BL-ICO

Từ v0.2, không share anchor mơ hồ trong một trang claim dài nếu có thể share URL riêng. Mỗi Claim ID có canonical URL riêng, nằm trong sitemap và machine claim index. Comment giscus dùng `pathname`, nên phản biện trên từng claim không bị trộn vào một thread chung.

Google xem `rel=canonical`, redirects và sitemap là các tín hiệu canonicalization; canonical vẫn là hint chứ không phải mệnh lệnh tuyệt đối. Vì vậy chỉ giữ **một origin chính**, tránh public hai bản HTML giống nhau ở hai host mà không có chiến lược canonical/redirect.


## Vòng index pilot sau khi public

1. Xác nhận root, `robots.txt`, `sitemap.xml` và 5–10 Claim URLs trả HTTP 200 khi mở logged-out.
2. Đưa sitemap vào Google Search Console nếu bạn có thể verify property.
3. Dùng URL Inspection cho root và một số claim quan trọng; request indexing có quota nên không spam toàn bộ 68 URL bằng tay.
4. Link nội bộ từ `claims.html` tới mọi claim; build v0.2 làm sẵn.
5. Đăng một số claim pilot trên social/profile với **canonical Claim URL**, không copy cả site thành nhiều origin.
6. Không chặn `OAI-SearchBot` nếu muốn có khả năng xuất hiện trong ChatGPT Search. `GPTBot` là crawler khác và có thể được policy riêng.
7. Đo BL-SRS: attention, understanding, objection quality, independent restatement, derivative ideas.
8. Critique truth-relevant → Issue Deep Audit → patch → version mới theo BL-PIRAL.

Google coi canonical tag, redirects và sitemap là canonicalization signals chứ không bảo đảm tuyệt đối URL nào được chọn. Vì vậy consistency giữa internal links, sitemap và `rel=canonical` quan trọng hơn việc tạo nhiều bản sao để "phủ SEO".
