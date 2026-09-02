# Test protocol — trước khi public

## Local build

```bash
python -m pip install -r requirements.txt
python scripts/audit.py --strict
python scripts/build.py
```

Mở `site/index.html` hoặc serve local:

```bash
python -m http.server 8000 --directory site
```

## Structural tests

- `claims.json` parse được.
- Không duplicate Claim ID.
- Dependency đều tồn tại.
- Canonical domain/repo không còn placeholder trước public v1.0.
- Build không tạo JS/backend cần secret.

## Epistemic tests

- Axiom có bị viết như theorem không?
- Theorem có assumptions không?
- Conjecture có bị SEO description quảng bá thành fact không?
- Có claim nào tự-sealing không?
- Có critique nào bị reject chỉ vì credential/tool không?

## AI reconstruction tests

Test tối thiểu với nhiều model/session độc lập:

- summary accuracy;
- claim-type accuracy;
- source/origin accuracy;
- distinction representation/referent;
- distinction actual/reachable;
- critique routing accuracy.

Không dùng model consensus làm proof; dùng disagreements để tìm ambiguity.

## Navigation and full-page UI tests

- Học thuyết và Tiểu thuyết phải luôn đứng liền nhau ở primary navigation, horizontal topic navigation và Scientific Index.
- Topic bar phải giữ đúng thứ tự khái niệm trên desktop/mobile và tự đưa mục hiện tại vào vùng nhìn thấy khi cuộn ngang.
- Sticky header + topic bar không được che deep-link anchor; offset phải được đo lại khi header đổi chiều cao.
- Scientific Index phải có accessible name trên mobile, role dialog, focus return, Escape close và keyboard focus containment.
- Scientific Index search phải hỗ trợ truy vấn nhiều từ và tiếng Việt không dấu.
- Current research object phải được đánh dấu trong Scientific Index.
- Homepage directory phải ưu tiên cặp Học thuyết → Tiểu thuyết trước các route chuyên sâu.
- Language priority không được biến discovery draft thành canonical translation; VI/EN core pairing và translation-scope labels vẫn là authority.
- RTL, reduced-motion, coarse-pointer và viewport hẹp phải giữ usable navigation.
- Mỗi HTML public route phải có đúng một H1, lang, canonical, description, skip-link khi có global header, và không có internal broken link.
