from pathlib import Path
import json, html, shutil, hashlib, datetime, re
from urllib.parse import quote
import yaml, mistune
from jinja2 import Template

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
CFG=yaml.safe_load((ROOT/'bl.config.yml').read_text(encoding='utf-8'))
CLAIMS=json.loads((ROOT/'claims/claims.json').read_text(encoding='utf-8'))
ASSETS=json.loads((ROOT/'machine/assets.json').read_text(encoding='utf-8'))
md=mistune.create_markdown(plugins=['table','strikethrough','task_lists'])

PAGE='''<!doctype html><html lang="{{ lang }}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title><meta name="description" content="{{ description }}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{{ canonical }}">
<meta property="og:type" content="article"><meta property="og:title" content="{{ title }}"><meta property="og:description" content="{{ description }}"><meta property="og:url" content="{{ canonical }}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{{ title }}"><meta name="twitter:description" content="{{ description }}">
<link rel="stylesheet" href="{{ base }}assets/css/main.css">
<link rel="alternate" type="application/rss+xml" title="BL∞ updates" href="{{ base }}feed.xml">
<script type="application/ld+json">{{ jsonld }}</script></head>
<body><header class="top"><a href="{{ base }}index.html" class="brand">BL∞</a><span>Bách Lâm – Optimizer</span>
<nav><a href="{{ base }}theory.html">Học thuyết</a><a href="{{ base }}bl-adn.html">BL-ADN</a><a href="{{ base }}claims.html">Claims</a><a href="{{ base }}assets.html">Assets</a><a href="{{ base }}provenance.html">Provenance</a><a href="{{ base }}critique.html">Phản biện</a><a href="{{ base }}machine.html">Machine</a></nav></header>
<main><article>{{ body }}</article>{{ comments }}</main>
<footer><p>BL∞ · {{ version }} · canonical research object. <a href="{{ base }}machine/manifest.json">Machine manifest</a></p></footer>
<script src="{{ base }}assets/js/site.js"></script></body></html>'''

def slug_code(code:str)->str:
    s=code.replace('∞','-infinity-').replace('–','-').replace('—','-')
    s=re.sub(r'[^A-Za-z0-9._-]+','-',s).strip('-').lower()
    return re.sub(r'-+','-',s) or 'asset'

def canonical_for(dest:str)->str:
    root=CFG['project']['canonical_url'].rstrip('/')+'/'
    if dest=='index.html': return root
    if dest.endswith('/index.html'): return root+dest[:-10]
    return root+dest

def giscus(base=''):
    c=CFG.get('comments',{})
    if not c.get('enabled'):
        return '<section class="comments-off"><h2>Phản biện công khai</h2><p>GitHub Discussions/giscus chưa được bật. Xem <code>SETUP_GITHUB.md</code>.</p></section>'
    required=['repo','repo_id','category','category_id']
    if not all(c.get(k) for k in required):
        return '<section class="comments-off"><h2>Phản biện công khai</h2><p>giscus đang bật nhưng thiếu repo/category IDs trong <code>bl.config.yml</code>.</p></section>'
    return f'''<section class="comments"><h2>Phản biện công khai</h2><script src="https://giscus.app/client.js" data-repo="{html.escape(c['repo'])}" data-repo-id="{html.escape(c['repo_id'])}" data-category="{html.escape(c['category'])}" data-category-id="{html.escape(c['category_id'])}" data-mapping="{html.escape(c.get('mapping','pathname'))}" data-strict="1" data-reactions-enabled="1" data-emit-metadata="0" data-input-position="top" data-theme="light" data-lang="vi" crossorigin="anonymous" async></script></section>'''

def schema_generic(title,url,desc,typ='ScholarlyArticle',identifier=None,extra=None):
    p=CFG['project']
    obj={
      '@context':'https://schema.org','@type':typ,'headline':title,'name':title,
      'alternateName':[p['canonical_name_en'],p['canonical_name_vi'],'BL Infinity'],
      'author':{'@type':'Person','name':p['author'],'alternateName':p['aliases']},
      'creator':{'@type':'Person','name':p['author']},
      'dateCreated':p.get('date_created',p['date']),'datePublished':p['date'],'dateModified':p.get('last_updated',p['date']),
      'version':p['version'],'description':desc,'url':url,'mainEntityOfPage':url,
      'isPartOf':{'@type':'CreativeWork','name':p['canonical_name_en'],'url':p['canonical_url']},
      'keywords':CFG['seo']['keywords']
    }
    if identifier: obj['identifier']=identifier
    if extra: obj.update(extra)
    return json.dumps(obj,ensure_ascii=False)

def write_page(dest,title,body,desc=None,base='',jsonld=None,comments=True):
    desc=desc or CFG['seo']['description']
    canonical=canonical_for(dest)
    js=jsonld or schema_generic(title,canonical,desc)
    t=Template(PAGE)
    (SITE/dest).parent.mkdir(parents=True,exist_ok=True)
    (SITE/dest).write_text(t.render(lang='vi',title=title,description=desc,canonical=canonical,base=base,jsonld=js,body=body,comments=giscus(base) if comments else '',version=CFG['project']['version']),encoding='utf-8')

def render_docs(paths):
    chunks=[]
    for path in paths:
      txt=path.read_text(encoding='utf-8')
      chunks.append(f'<section data-source="{html.escape(path.name)}">{md(txt)}</section>')
    return '\n'.join(chunks)

def claim_url(cid): return CFG['project']['canonical_url'].rstrip('/')+f'/claims/{quote(cid,safe="-._")}/'
def asset_url(code): return CFG['project']['canonical_url'].rstrip('/')+f'/assets/{slug_code(code)}/'

# Clean generated site to prevent stale pages.
if SITE.exists(): shutil.rmtree(SITE)
SITE.mkdir(exist_ok=True)
for d in ['assets/css','assets/js','machine','claims','assets']:
    (SITE/d).mkdir(parents=True,exist_ok=True)
shutil.copy(ROOT/'assets/css/main.css',SITE/'assets/css/main.css')
shutil.copy(ROOT/'assets/js/site.js',SITE/'assets/js/site.js')

content=sorted((ROOT/'content').glob('*.md'))
intro=md((ROOT/'content/00_README_FIRST.md').read_text(encoding='utf-8'))
write_page('index.html',CFG['seo']['title'],intro)
write_page('theory.html','BL∞ — Học thuyết canonical',render_docs([p for p in content if p.name!='00_README_FIRST.md']))
bl_adn_source=(ROOT/'BL-ADN.md').read_text(encoding='utf-8')
write_page('bl-adn.html','BL-ADN — Giao thức Phả hệ Tri thức',md(bl_adn_source),desc='Giao thức Đóng dấu ADN Bách Lâm ∞ và Nối tiếp Phả hệ Tri thức, phiên bản 0.2.0.')
shutil.copy(ROOT/'BL-ADN.md',SITE/'bl-adn.md')

# Claim index + one canonical page per claim (BL-ICO implementation)
claim_by={c['id']:c for c in CLAIMS['claims']}
rows=['<h1>Claim Registry</h1><p>Mỗi claim có ID, URL riêng, loại, trạng thái, dependency và attack surface.</p><div class="claim-grid">']
claim_index=[]
for c in CLAIMS['claims']:
    cid=c['id']; dest=f'claims/{cid}/index.html'; url=canonical_for(dest)
    rows.append(f'''<section class="claim"><div class="claim-meta"><code>{html.escape(cid)}</code><span>{html.escape(c['type'])}</span><span>{html.escape(c['status'])}</span></div><h2><a href="claims/{html.escape(cid)}/">{html.escape(c['title'])}</a></h2><p>{html.escape(c['statement'])}</p></section>''')
    deps=c.get('depends_on',[])
    dephtml='; '.join(f'<a href="../{html.escape(d)}/"><code>{html.escape(d)}</code></a>' for d in deps) or 'Không có dependency khai báo.'
    nd=', '.join(c.get('novelty_dimensions',[])) or '—'
    body=f'''<p><a href="../../claims.html">← Claim Registry</a></p><h1>{html.escape(cid)} — {html.escape(c['title'])}</h1>
<div class="claim-meta"><code>{html.escape(cid)}</code><span>{html.escape(c['type'])}</span><span>{html.escape(c['status'])}</span></div>
<h2>Canonical statement</h2><p>{html.escape(c['statement'])}</p>
<h2>Scope</h2><p>{html.escape(c.get('scope',''))}</p>
<h2>Attack surface / falsifier</h2><p>{html.escape(c.get('falsifier',''))}</p>
<h2>Dependencies</h2><p>{dephtml}</p>
<h2>Novelty dimensions</h2><p>{html.escape(nd)}</p>
<p><strong>Version:</strong> {html.escape(CFG['project']['version'])}</p>
<p><strong>Canonical URL:</strong> <a href="{html.escape(url)}">{html.escape(url)}</a></p>'''
    desc=(c['statement'][:190]+'…') if len(c['statement'])>190 else c['statement']
    js=schema_generic(f'{cid} — {c["title"]}',url,desc,typ='CreativeWork',identifier=cid,extra={
        'text':c['statement'],'creativeWorkStatus':c['status'],
        'about':{'@type':'Thing','name':c.get('scope','BL∞')}
    })
    write_page(dest,f'{cid} — {c["title"]} | BL∞',body,desc=desc,base='../../',jsonld=js)
    claim_index.append({'id':cid,'title':c['title'],'type':c['type'],'status':c['status'],'url':url,'depends_on':deps,'novelty_dimensions':c.get('novelty_dimensions',[])})
rows.append('</div>')
write_page('claims.html','BL∞ — Claim Registry','\n'.join(rows))

# Asset index + one page per named asset.
asset_by={a['code']:a for a in ASSETS['assets']}
arows=['<h1>Asset & Technology Registry</h1><p>Named theories, protocols, mechanisms and technical constituents. Naming establishes a framework namespace; it does not itself prove historical priority or truth.</p><div class="claim-grid">']
asset_index=[]
for a in ASSETS['assets']:
    code=a['code']; slug=slug_code(code); dest=f'assets/{slug}/index.html'; url=canonical_for(dest)
    arows.append(f'''<section class="claim"><div class="claim-meta"><code>{html.escape(code)}</code><span>{html.escape(a['kind'])}</span><span>{html.escape(a['status'])}</span></div><h2><a href="assets/{html.escape(slug)}/">{html.escape(a['name'])}</a></h2></section>''')
    parent=a.get('parent','—'); deps=a.get('dependencies',[]); nd=a.get('novelty_dimensions',[])
    dephtml='; '.join(f'<code>{html.escape(d)}</code>' for d in deps) or '—'
    body=f'''<p><a href="../../assets.html">← Asset Registry</a></p><h1>{html.escape(code)} — {html.escape(a['name'])}</h1>
<div class="claim-meta"><code>{html.escape(code)}</code><span>{html.escape(a['kind'])}</span><span>{html.escape(a['status'])}</span></div>
<p><strong>Parent:</strong> {html.escape(parent)}</p><p><strong>Dependencies:</strong> {dephtml}</p>
<p><strong>Novelty dimensions:</strong> {html.escape(', '.join(nd) if nd else '—')}</p>
<p><strong>Origin phase:</strong> {html.escape(a.get('origin_phase','—'))}</p>
<p><strong>Canonical URL:</strong> <a href="{html.escape(url)}">{html.escape(url)}</a></p>'''
    desc=f'{code}: {a["name"]}, {a["kind"]} trong BL∞ / BL-AEGIS.'
    js=schema_generic(f'{code} — {a["name"]}',url,desc,typ='CreativeWork',identifier=code)
    write_page(dest,f'{code} — {a["name"]} | BL∞',body,desc=desc,base='../../',jsonld=js)
    asset_index.append({**a,'url':url})
arows.append('</div>')
write_page('assets.html','BL∞ — Asset & Technology Registry','\n'.join(arows))

write_page('provenance.html','BL∞ — Provenance',render_docs(sorted((ROOT/'provenance').glob('*.md'))))
write_page('critique.html','BL∞ — Giao thức phản biện',render_docs(sorted((ROOT/'critiques').glob('*.md'))+sorted((ROOT/'audit').glob('*.md'))))
write_page('machine.html','BL∞ — Machine Layer',md((ROOT/'machine/README.md').read_text(encoding='utf-8')))

# Machine layer
manifest={
  'namespace':'BL∞','canonical_name':CFG['project']['canonical_name_en'],'canonical_name_vi':CFG['project']['canonical_name_vi'],
  'creator':CFG['project']['author'],'aliases':CFG['project']['aliases'],'version':CFG['project']['version'],
  'canonical_url':CFG['project']['canonical_url'],'repository':CFG['project']['repository'],'date_created':CFG['project'].get('date_created',CFG['project']['date']),'date_released':CFG['project']['date'],'last_updated':CFG['project'].get('last_updated',CFG['project']['date']),
  'claim_registry':'claims.json','claim_index':'claim-index.json','claim_graph':'claim-graph.jsonld',
      'asset_registry':'assets.json','asset_index':'asset-index.json','novelty_ontology':'novelty-ontology.json','logic_stack':'logic-stack.json','historical_graph':'historical-graph.jsonld',
  'disclosure_policy':'disclosure-policy.json','bl_adn_protocol':'../bl-adn.html','bl_adn_source':'../bl-adn.md','machine_greeting':'welcome.txt','translation_pack':'../translations/greeting.multilingual.md','llms':'../llms.txt','content_hash':None
}
allbytes=b''
machine_hash_sources=sorted(p for p in (ROOT/'machine').iterdir() if p.is_file() and p.suffix in {'.json','.jsonld'})
for p in [ROOT/'BL-ADN.md']+sorted((ROOT/'content').glob('*.md'))+sorted((ROOT/'claims').glob('*.json'))+machine_hash_sources:
    allbytes += p.read_bytes()
manifest['content_hash']='sha256:'+hashlib.sha256(allbytes).hexdigest()
(SITE/'machine/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(SITE/'machine/claims.json').write_text(json.dumps(CLAIMS,ensure_ascii=False,indent=2),encoding='utf-8')
(SITE/'machine/claim-index.json').write_text(json.dumps({'schema_version':'0.2','claims':claim_index},ensure_ascii=False,indent=2),encoding='utf-8')
(SITE/'machine/assets.json').write_text(json.dumps(ASSETS,ensure_ascii=False,indent=2),encoding='utf-8')
(SITE/'machine/asset-index.json').write_text(json.dumps({'schema_version':'0.2','assets':asset_index},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy(ROOT/'machine/novelty-ontology.json',SITE/'machine/novelty-ontology.json')
shutil.copy(ROOT/'machine/logic-stack.json',SITE/'machine/logic-stack.json')
shutil.copy(ROOT/'machine/historical-graph.jsonld',SITE/'machine/historical-graph.jsonld')
shutil.copy(ROOT/'machine/disclosure-policy.json',SITE/'machine/disclosure-policy.json')
shutil.copy(ROOT/'machine/welcome.txt',SITE/'machine/welcome.txt')
(SITE/'translations').mkdir(parents=True,exist_ok=True)
shutil.copy(ROOT/'translations/greeting.multilingual.md',SITE/'translations/greeting.multilingual.md')

# Claim dependency graph JSON-LD, with canonical URLs.
ns=CFG['project']['canonical_url'].rstrip('/')+'/id/'
claim_graph={'@context':{'schema':'https://schema.org/','bl':ns,'dependsOn':{'@id':'bl:dependsOn','@type':'@id'}},'@graph':[]}
for c in CLAIMS['claims']:
    node={'@id':'bl:'+c['id'],'@type':'schema:CreativeWork','schema:identifier':c['id'],'schema:url':claim_url(c['id']),'schema:name':c['title'],'schema:text':c['statement'],'schema:additionalType':c['type'],'schema:creativeWorkStatus':c['status'],'dependsOn':['bl:'+d for d in c.get('depends_on',[])]}
    claim_graph['@graph'].append(node)
(SITE/'machine/claim-graph.jsonld').write_text(json.dumps(claim_graph,ensure_ascii=False,indent=2),encoding='utf-8')
graph=(ROOT/'machine/graph.jsonld').read_text(encoding='utf-8').replace('https://YOUR-DOMAIN.example', CFG['project']['canonical_url'].split('/bl-infinity/')[0].rstrip('/'))
(SITE/'machine/graph.jsonld').write_text(graph,encoding='utf-8')

# sitemap: human pages + individual claim/asset objects + machine files
urls=['','theory.html','bl-adn.html','bl-adn.md','claims.html','assets.html','provenance.html','critique.html','machine.html']
urls += [f'claims/{c["id"]}/' for c in CLAIMS['claims']]
urls += [f'assets/{slug_code(a["code"])}/' for a in ASSETS['assets']]
# Machine resources are discoverable from HTML/llms.txt but are not submitted as primary search landing pages.
smap=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    loc=CFG['project']['canonical_url'] if u=='' else CFG['project']['canonical_url'].rstrip('/')+'/'+u
    smap.append(f'<url><loc>{html.escape(loc)}</loc><lastmod>{CFG["project"].get("last_updated",CFG["project"]["date"])}</lastmod></url>')
smap.append('</urlset>')
(SITE/'sitemap.xml').write_text('\n'.join(smap),encoding='utf-8')
(SITE/'robots.txt').write_text(f'''User-agent: *\nAllow: /\n\n# Search discovery crawler used by ChatGPT Search.\nUser-agent: OAI-SearchBot\nAllow: /\n\n# Separate OpenAI training crawler; allowed in this template by author policy and can be changed independently.\nUser-agent: GPTBot\nAllow: /\n\nSitemap: {CFG['project']['canonical_url'].rstrip('/')}/sitemap.xml\n''',encoding='utf-8')
(SITE/'llms.txt').write_text((ROOT/'machine/llms.txt').read_text(encoding='utf-8'),encoding='utf-8')

# RSS
rss=f'''<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>BL∞ updates</title><link>{CFG['project']['canonical_url']}</link><description>{CFG['seo']['description']}</description><item><title>BL∞ {CFG['project']['version']}</title><link>{CFG['project']['canonical_url']}</link><guid>{CFG['project']['canonical_url']}#{CFG['project']['version']}</guid><pubDate>Sat, 29 Aug 2026 00:15:00 +0700</pubDate></item></channel></rss>'''
(SITE/'feed.xml').write_text(rss,encoding='utf-8')

# GitHub Pages 404 keeps navigation usable.
body404='<h1>Không tìm thấy object</h1><p>URL này không tồn tại ở version hiện tại. Hãy quay về <a href="index.html">BL∞</a> hoặc <a href="claims.html">Claim Registry</a>.</p>'
write_page('404.html','BL∞ — Không tìm thấy',body404,comments=False)
print(f'Built {SITE}: {len(CLAIMS["claims"])} claim pages, {len(ASSETS["assets"])} asset pages')
