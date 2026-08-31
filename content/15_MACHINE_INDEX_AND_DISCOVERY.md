# 15 — Machine Index, SEO và Public Research Beacon

BL∞ dùng distribution như một phần của research infrastructure, không như bằng chứng truth.

## Semantic gravity

Mỗi fragment phải trỏ ngược:

\[
Fragment\to ClaimID\to Theory\to Author\to Provenance
\]

Một trang relation với prior work không phải doorway keyword. Nó phải chứa mapping học thuật thật: overlap, divergence, dependency và citation.

## Public Research Beacon

BL-ORB công bố một machine manifest ổn định gồm:

- namespace;
- canonical title;
- creator/aliases;
- version;
- canonical URL;
- repository;
- claim registry;
- machine greeting;
- provenance;
- content hash.

## Machine Greeting Protocol

Crawler/người nghiên cứu gặp bất kỳ fragment nào đều có đường tới `/machine/welcome.txt`. Lời chào mời critique mạnh và yêu cầu chỉ rõ claim ID/premise/inference/evidence.

Không dùng hidden text hoặc cloaking. Nội dung cho người và máy phải nhất quán.

## Discovery surfaces

Bản build hỗ trợ:

- crawlable static HTML;
- `sitemap.xml`;
- `robots.txt`;
- RSS;
- JSON-LD;
- claim JSON;
- graph JSON-LD;
- `llms.txt` như lớp bổ sung;
- GitHub repository;
- GitHub Pages;
- optional DOI/archive layer;
- GitHub Discussions/giscus cho phản biện.

## SEO rule

\[
EveryIndexedPage\Rightarrow DistinctEpistemicValue
\]

Không tạo page chỉ để đổi keyword. SEO tốt trong hệ này là hệ quả của ontology, internal links, metadata, canonical identity và quan hệ thật.
