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
