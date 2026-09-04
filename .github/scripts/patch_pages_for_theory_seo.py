#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[2]
p = root / '.github/workflows/pages.yml'
text = p.read_text(encoding='utf-8')

text = text.replace(
    'mkdir -p _site/novel _site/assets/css _site/assets/js _site/books',
    'mkdir -p _site/novel _site/assets/css _site/assets/js _site/assets/brand _site/books'
)
text = text.replace(
    'cp index.html theory.html academic-freedom.html academic-democracy.html author.html projects.html authors-promise.html robots.txt sitemap.xml _site/',
    'cp index.html theory.html academic-freedom.html academic-democracy.html author.html projects.html authors-promise.html robots.txt sitemap.xml sitemap-images.xml _site/'
)
needle = '          cp assets/js/site.js assets/js/reader.js assets/js/reader-markdown.js _site/assets/js/\n'
insert = needle + '          cp -R assets/brand/. _site/assets/brand/\n'
if 'cp -R assets/brand/. _site/assets/brand/' not in text:
    text = text.replace(needle, insert)

assert_needle = '          test -f _site/assets/js/reader-markdown.js\n'
assert_block = '''          test -f _site/assets/js/reader-markdown.js
          test -f _site/assets/brand/theory-favicon.svg
          test -f _site/assets/brand/favicon.ico
          test -f _site/assets/brand/apple-touch-icon.png
          test -f _site/assets/brand/og/cover-human-development.jpg
          test -f _site/assets/brand/og/cover-kevin-research-studio.jpg
          test -f _site/assets/brand/og/cover-dual-pole.jpg
          test -f _site/assets/brand/og/cover-100-works.jpg
          test -f _site/assets/brand/og/cover-real-application-value.jpg
          test -f _site/sitemap-images.xml
'''
if 'test -f _site/assets/brand/theory-favicon.svg' not in text:
    text = text.replace(assert_needle, assert_block)

validation_needle = "          print('Shared reader + Vietnamese typography + HCM science + clean novel + Kevin Research Studio validation: PASS')\n"
validation_block = '''          # THEORY social/SEO contract: crawler-safe raster previews + lightweight vector/favicon.
          theory_pages = {
              root / 'research/human-development/index.html': 'cover-human-development.jpg',
              root / 'research/human-development/kevin-nt/index.html': 'cover-kevin-research-studio.jpg',
              root / 'research/human-development/kevin-nt/studio/index.html': 'cover-kevin-research-studio.jpg',
              root / 'research/human-development/kevin-nt/tien-hoa-luong-cuc.html': 'cover-dual-pole.jpg',
              root / 'research/human-development/kevin-nt/attribution-benchmark.html': 'cover-real-application-value.jpg',
              root / 'books/kevin-intellectual-map/index.html': 'cover-100-works.jpg',
          }
          for path, cover in theory_pages.items():
              text = path.read_text(encoding='utf-8')
              required = (
                  'rel="icon" type="image/svg+xml"',
                  'rel="apple-touch-icon"',
                  'property="og:image"',
                  'property="og:image:width" content="1200"',
                  'property="og:image:height" content="630"',
                  'property="og:image:alt"',
                  'name="twitter:card" content="summary_large_image"',
                  'name="twitter:image"',
                  cover,
              )
              for marker in required:
                  if marker not in text:
                      raise SystemExit(f'THEORY SEO marker missing {marker}: {path.relative_to(root)}')

          brand = root / 'assets/brand'
          size_limits = {
              brand / 'theory-favicon.svg': 6_000,
              brand / 'favicon.ico': 20_000,
              brand / 'apple-touch-icon.png': 30_000,
              brand / 'og/cover-human-development.jpg': 180_000,
              brand / 'og/cover-kevin-research-studio.jpg': 180_000,
              brand / 'og/cover-dual-pole.jpg': 180_000,
              brand / 'og/cover-100-works.jpg': 180_000,
              brand / 'og/cover-real-application-value.jpg': 180_000,
          }
          for path, limit in size_limits.items():
              if not path.exists() or path.stat().st_size <= 0 or path.stat().st_size > limit:
                  raise SystemExit(f'THEORY asset size/availability failed: {path.relative_to(root)} size={path.stat().st_size if path.exists() else "MISSING"} limit={limit}')

          if not (root / 'sitemap-images.xml').exists():
              raise SystemExit('THEORY image sitemap missing')

          print('Shared reader + Vietnamese typography + HCM science + clean novel + Kevin Research Studio + THEORY social SEO validation: PASS')
'''
if 'THEORY social/SEO contract' not in text:
    text = text.replace(validation_needle, validation_block)

p.write_text(text, encoding='utf-8')
print('Patched curated Pages workflow for THEORY SEO assets: PASS')
