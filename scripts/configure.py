from pathlib import Path
import argparse,yaml
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--github',required=True,help='GitHub username or organization')
p.add_argument('--repo',default='bl-infinity')
p.add_argument('--url',default=None,help='Canonical BL∞ URL; default GitHub Pages URL')
a=p.parse_args()
url=a.url or f'https://{a.github}.github.io/{a.repo}/'
if not url.endswith('/'): url+='/'
config=ROOT/'bl.config.yml'
d=yaml.safe_load(config.read_text(encoding='utf-8'))
d['project']['repository']=f'{a.github}/{a.repo}'
d['project']['canonical_url']=url
d['comments']['repo']=f'{a.github}/{a.repo}'
config.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
repls={
 'YOUR_GITHUB_USERNAME':a.github,
 'https://YOUR-DOMAIN.example/bl-infinity/':url,
 'https://YOUR-DOMAIN.example':url.rstrip('/').removesuffix('/bl-infinity'),
}
for rel in ['CITATION.cff','.github/ISSUE_TEMPLATE/config.yml','machine/graph.jsonld']:
    f=ROOT/rel
    if f.exists():
        text=f.read_text(encoding='utf-8')
        for x,y in repls.items(): text=text.replace(x,y)
        f.write_text(text,encoding='utf-8')

# Restrict giscus embedding to the configured site origin + localhost for testing.
from urllib.parse import urlparse
origin=urlparse(url).scheme+'://'+urlparse(url).netloc
giscus=ROOT/'giscus.json'
if giscus.exists():
    import json
    gd={'origins':[origin],'originsRegex':[r'http://localhost:[0-9]+'],'defaultCommentOrder':'oldest'}
    giscus.write_text(json.dumps(gd,ensure_ascii=False,indent=2),encoding='utf-8')

print(f'Configured repository: {a.github}/{a.repo}')
print(f'Canonical URL: {url}')
print('Next: python scripts/audit.py && python scripts/build.py')
