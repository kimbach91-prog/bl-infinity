from pathlib import Path
import json

source_path = Path(__file__).with_name('build_discovery.py')
source = source_path.read_text(encoding='utf-8')

# Compatibility repair for the first multilingual discovery template release.
# Deterministic + idempotent: once the template source is corrected, this no-ops.
broken = "\n}\n\nVI_KEYWORDS = ["
fixed = "\n}\n}\n\nVI_KEYWORDS = ["
if broken in source and fixed not in source:
    source = source.replace(broken, fixed, 1)

code = compile(source, str(source_path), 'exec')
namespace = {'__file__': str(source_path), '__name__': '__main__'}
exec(code, namespace, namespace)

# Entity-resolution pass: make the human author resolvable from every public HTML object.
site = source_path.resolve().parents[1] / 'site'
author_url = 'https://kimbach91-prog.github.io/bl-infinity/author.html'
person_id = author_url + '#person'
person = {
    '@context': 'https://schema.org',
    '@type': 'Person',
    '@id': person_id,
    'name': 'Lâm Kim Bách',
    'alternateName': ['Bách Lâm', 'Bách Lâm – Optimizer', 'Lam Kim Bach', 'Bach Lam'],
    'url': author_url,
    'sameAs': [
        'https://m.facebook.com/lam.kimbach/',
        'https://github.com/kimbach91-prog'
    ],
    'knowsAbout': [
        'BL∞', 'Academic Democracy', 'Dân chủ Học thuật', 'open scholarship',
        'research provenance', 'epistemic governance', 'assisted scholarship'
    ]
}
person_script = '<script type="application/ld+json">' + json.dumps(person, ensure_ascii=False) + '</script>'
author_link = f'<link rel="author" href="{author_url}">'

for page in site.rglob('*.html'):
    text = page.read_text(encoding='utf-8')
    additions = []
    if 'rel="author"' not in text:
        additions.append(author_link)
    if person_id not in text:
        additions.append(person_script)
    if additions and '</head>' in text:
        text = text.replace('</head>', '\n'.join(additions) + '\n</head>', 1)
        page.write_text(text, encoding='utf-8')

# Upgrade the dedicated author URL to a ProfilePage entity while keeping Person sameAs data.
author_page = site / 'author.html'
if author_page.exists():
    text = author_page.read_text(encoding='utf-8')
    profile = {
        '@context': 'https://schema.org',
        '@type': 'ProfilePage',
        '@id': author_url + '#profile',
        'url': author_url,
        'dateModified': '2026-08-30',
        'mainEntity': {'@id': person_id}
    }
    marker = author_url + '#profile'
    if marker not in text and '</head>' in text:
        text = text.replace('</head>', '<script type="application/ld+json">' + json.dumps(profile, ensure_ascii=False) + '</script>\n</head>', 1)
        author_page.write_text(text, encoding='utf-8')
