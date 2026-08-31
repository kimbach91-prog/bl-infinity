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
TINDEX=json.loads((ROOT/'translations/translation-index.json').read_text(encoding='utf-8'))
md=mistune.create_markdown(plugins=['table','strikethrough','task_lists'])

PAGE='''<!doctype html><html lang="{{ lang }}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title><meta name="description" content="{{ description }}">
<meta name="robots" content="{{ robots }}">
<link rel="canonical" href="{{ canonical }}">
<meta property="og:type" content="article"><meta property="og:title" content="{{ title }}"><meta property="og:description" content="{{ description }}"><meta property="og:url" content="{{ canonical }}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{{ title }}"><meta name="twitter:description" content="{{ description }}">
<link rel="stylesheet" href="{{ base }}assets/css/main.css">
<link rel="alternate" type="application/rss+xml" title="BL∞ updates" href="{{ base }}feed.xml">
<script type="application/ld+json">{{ jsonld }}</script></head>
<body><header class="top"><a href="{{ base }}index.html" class="brand">BL∞</a><span>Bách Lâm – Optimizer</span>
<nav><a href="{{ base }}theory.html">Học thuyết</a><a href="{{ base }}academic-democracy.html">Dân chủ Học thuật</a><a href="{{ base }}bl-adn.html">BL-ADN</a><a href="{{ base }}claims.html">Claims</a><a href="{{ base }}assets.html">Assets</a><a href="{{ base }}author.html">Tác giả</a><a href="{{ base }}provenance.html">Provenance</a><a href="{{ base }}critique.html">Phản biện</a><a href="{{ base }}machine.html">Machine</a></nav></header>
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
    author_url=p['canonical_url'].rstrip('/')+'/author.html'
    obj={
      '@context':'https://schema.org','@type':typ,'headline':title,'name':title,
      'alternateName':[p['canonical_name_en'],p['canonical_name_vi'],'BL Infinity'],
      'author':{'@type':'Person','@id':author_url+'#person','name':p['author'],'alternateName':p['aliases'],'url':author_url,'sameAs':['https://m.facebook.com/lam.kimbach/','https://github.com/kimbach91-prog']},
      'creator':{'@id':author_url+'#person'},
      'dateCreated':p.get('date_created',p['date']),'datePublished':p['date'],'dateModified':p.get('last_updated',p['date']),
      'version':p['version'],'description':desc,'url':url,'mainEntityOfPage':url,
      'isPartOf':{'@type':'CreativeWork','name':p['canonical_name_en'],'url':p['canonical_url']},
      'inLanguage':'vi','keywords':CFG['seo']['keywords']
    }
    if identifier:
      obj['identifier']=identifier
      obj.pop('alternateName',None)
      obj['keywords']=[identifier,title]
    if extra: obj.update(extra)
    return json.dumps(obj,ensure_ascii=False)

def write_page(dest,title,body,desc=None,base='',jsonld=None,comments=True,robots='index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1'):
    desc=desc or CFG['seo']['description']
    canonical=canonical_for(dest)
    js=jsonld or schema_generic(title,canonical,desc)
    t=Template(PAGE)
    (SITE/dest).parent.mkdir(parents=True,exist_ok=True)
    (SITE/dest).write_text(t.render(lang='vi',title=title,description=desc,canonical=canonical,base=base,jsonld=js,body=body,comments=giscus(base) if comments else '',robots=robots,version=CFG['project']['version']),encoding='utf-8')

def shift_headings(fragment):
    return re.sub(
        r'<(/?)h([1-5])(\b[^>]*)>',
        lambda match: f'<{match.group(1)}h{int(match.group(2))+1}{match.group(3)}>',
        fragment,
        flags=re.I,
    )

def render_docs(paths,page_heading):
    chunks=[]
    for path in paths:
      txt=path.read_text(encoding='utf-8')
      chunks.append(f'<section data-source="{html.escape(path.name)}">{shift_headings(md(txt))}</section>')
    return f'<h1>{html.escape(page_heading)}</h1>\n'+'\n'.join(chunks)

def author_spotlight():
    return '''<section class="author-spotlight" aria-labelledby="author-spotlight-title">
<p class="eyebrow">Tác giả &amp; phả hệ</p><h2 id="author-spotlight-title">Lâm Kim Bách · Bách Lâm · Optimizer</h2>
<p><strong>Lâm Kim Bách</strong> là định danh con người; <strong>Bách Lâm</strong> là định danh tác quyền/phả hệ; <strong>Optimizer</strong> là định danh hệ/phương pháp công khai. Ba vai trò được nối nhưng không bị đánh đồng.</p>
<p><a class="primary-link" href="author.html">Xem hồ sơ tác giả canonical</a> · <a href="provenance.html">Kiểm tra provenance</a> · <a href="critique.html">Phản biện công khai</a></p>
</section>'''

def topic_entry_points():
    return '''<section class="topic-entry-points" aria-labelledby="topic-entry-title">
<p class="eyebrow">Lối vào theo chủ đề</p><h2 id="topic-entry-title">Bốn cụm tri thức chính của BL∞</h2>
<div class="topic-grid">
<section><h3><a href="academic-democracy.html">Dân chủ Học thuật</a></h3><p>Mở quyền tham gia tạo tri thức nhưng giữ trọng lượng bằng chứng, phản biện và quyền phủ quyết của thực tại.</p></section>
<section><h3><a href="bl-adn.html">Phả hệ tri thức &amp; research provenance</a></h3><p>Truy nguyên tác giả, nguồn, vai trò formalization và lịch sử phiên bản ở cấp object.</p></section>
<section><h3><a href="machine.html">Nghiên cứu máy đọc được</a></h3><p>Claim ID, registry, dependency graph và public machine contracts giúp người lẫn AI kiểm tra đúng canonical object.</p></section>
<section><h3><a href="critique.html">Phản biện công khai</a></h3><p>Gắn phản ví dụ, evidence và lỗi suy luận vào đúng claim để sửa đổi có thể truy vết.</p></section>
</div></section>'''

def home_directory():
    entries = [
        ('theory.html', 'Học thuyết canonical', 'Toàn bộ chương công khai, tiên đề, mệnh đề, cơ chế và câu hỏi mở của BL∞.'),
        ('academic-democracy.html', 'Dân chủ Học thuật', 'Tuyên ngôn mở quyền tham gia tạo tri thức mà không bình quân hóa trọng lượng bằng chứng.'),
        ('academic-democracy-technology.html', 'Hồ sơ công nghệ', 'Claim graph, provenance, evidence routing, versioning, AI và ranh giới an toàn vận hành.'),
        ('bl-adn.html', 'BL-ADN', 'Giao thức giữ tên người tạo ra, phả hệ object, vai trò đóng góp và lịch sử phiên bản.'),
        ('claims.html', 'Claim Registry', 'Mỗi mệnh đề có ID, loại, phạm vi, dependency, trạng thái và bề mặt bác bỏ riêng.'),
        ('assets.html', 'Asset Registry', 'Danh mục học thuyết, protocol, mechanism và cấu kiện được định danh trong BL-lineage.'),
        ('author.html', 'Tác giả', 'Hồ sơ canonical của Lâm Kim Bách, định danh tác quyền Bách Lâm và hệ/phương pháp Optimizer.'),
        ('languages.html', 'Ngôn ngữ', 'Chọn bản đọc tiếng Việt, English core hoặc các bản khám phá có ghi rõ phạm vi chất lượng.'),
        ('provenance.html', 'Provenance', 'Kiểm tra nguồn gốc, chronology, quan hệ phái sinh, formalization và giới hạn tuyên bố ưu tiên.'),
        ('critique.html', 'Phản biện', 'Đưa counterexample, evidence, lỗi logic hoặc xung đột provenance vào đúng object.'),
        ('machine.html', 'Machine Layer', 'Manifest, graph, registry và public contracts để hệ thống máy tái dựng đúng BL∞.'),
        ('academic-democracy/discovery.html', 'Discovery đa ngôn ngữ', 'Chỉ mục thuật ngữ và lối truy xuất về cùng object Dân chủ Học thuật canonical.'),
    ]
    items = ''.join(
        '<li><a href="'+html.escape(href, quote=True)+'"><strong>'+html.escape(label)+'</strong>'
        '<span>'+html.escape(description)+'</span></a></li>'
        for href, label, description in entries
    )
    return '''<nav class="home-directory" aria-labelledby="home-directory-title">
<p class="eyebrow">Mục lục toàn hệ</p>
<h2 id="home-directory-title">Tất cả lối vào công khai</h2>
<p class="home-directory-intro">Menu thu gọn phía trên phục vụ thao tác nhanh. Danh mục dưới đây luôn hiển thị đầy đủ trên trang chủ để người đọc không phải mở menu mới biết BL∞ đang có những lớp nào.</p>
<ul class="home-directory-grid">'''+items+'''</ul></nav>'''

def home_snapshot():
    chapter_count=max(0,len(list((ROOT/'content').glob('*.md')))-1)
    claim_count=len(CLAIMS.get('claims',[]))
    asset_count=len(ASSETS.get('assets',[]))
    discovery_count=max(0,len(TINDEX.get('discovery_editions',{}).get('languages',{}))-1)
    return f'''<section class="system-snapshot" aria-labelledby="system-snapshot-title">
<p class="eyebrow">Bề mặt đã materialize</p><h2 id="system-snapshot-title">Một hệ nghiên cứu có thể đọc, truy nguyên và phản biện</h2>
<div class="snapshot-grid">
<div class="snapshot-card"><strong>{chapter_count}</strong><span>chương học thuyết công khai sau trang dẫn nhập</span></div>
<div class="snapshot-card"><strong>{claim_count}</strong><span>claim có định danh và bề mặt kiểm tra riêng</span></div>
<div class="snapshot-card"><strong>{asset_count}</strong><span>cấu kiện trong Asset &amp; Technology Registry</span></div>
<div class="snapshot-card"><strong>2 + {discovery_count}</strong><span>bản đọc chính + bản khám phá đa ngôn ngữ có ghi rõ trạng thái</span></div>
</div></section>'''

def home_body():
    source=(ROOT/'content/00_README_FIRST.md').read_text(encoding='utf-8')
    marker='<!-- HOME_DIRECTORY -->'
    if marker not in source:
        raise ValueError('content/00_README_FIRST.md is missing HOME_DIRECTORY marker')
    before,after=source.split(marker,1)
    return md(before)+home_directory()+home_snapshot()+md(after)+topic_entry_points()+author_spotlight()

def language_hub_body():
    discovery=TINDEX.get('discovery_editions',{}).get('languages',{})
    cards=[]
    for code,item in discovery.items():
        if code=='en':
            continue
        cards.append(
            '<li><a href="'+html.escape(item['route'],quote=True)+'" '
            'hreflang="'+html.escape(item['hreflang'],quote=True)+'" '
            'lang="'+html.escape(item['hreflang'],quote=True)+'">'+html.escape(item['name'])+'</a>'
            '<span class="status-badge status-draft">Bản khám phá · AI draft</span>'
            '<small>'+html.escape(item['known_gap'])+'</small></li>'
        )
    return '''<h1>Ngôn ngữ &amp; phạm vi bản dịch</h1>
<p>BL∞ không dùng một nút đổi ngôn ngữ để ngụ ý rằng mọi trang đã được dịch đầy đủ. Mỗi lựa chọn dưới đây công khai đúng phạm vi và trạng thái của nó.</p>
<section class="language-tier"><h2>Bản đọc chính</h2><ul class="language-grid">
<li><a href="theory.html" hreflang="vi" lang="vi">Tiếng Việt</a><span class="status-badge status-ready">Canonical đầy đủ</span><small>Nguồn đọc công khai đầy đủ và ưu tiên khi có tranh chấp câu chữ.</small></li>
<li><a href="en/theory.html" hreflang="en" lang="en">English</a><span class="status-badge status-core">Core research edition</span><small>Phiên bản lõi, chưa phải bản dịch từng dòng của toàn bộ corpus.</small></li>
</ul></section>
<section class="language-tier"><h2>Dân chủ Học thuật — 11 bản khám phá</h2>
<p>Các trang này là bản tóm lược để khám phá và truy xuất, không thay thế tuyên ngôn tiếng Việt đầy đủ; nội dung chưa được coi là bản dịch học thuật đã duyệt.</p>
<ul class="language-grid">'''+''.join(cards)+'''</ul></section>
<p><strong>Không tự chuyển hướng theo ngôn ngữ.</strong> Người đọc luôn tự chọn phiên bản; canonical, provenance và trạng thái review vẫn hiển thị độc lập.</p>'''

def require_public_files(paths):
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f'Public allowlist file missing: {path.relative_to(ROOT)}')
    return paths

def claim_url(cid): return CFG['project']['canonical_url'].rstrip('/')+f'/claims/{quote(cid,safe="-._")}/'
def asset_url(code): return CFG['project']['canonical_url'].rstrip('/')+f'/assets/{slug_code(code)}/'

# BL-CPR fail-closed public allowlists. Directory presence alone never grants publication.
PUBLIC_PROVENANCE_FILES=require_public_files([
    ROOT/'provenance/00_PUBLIC_PROVENANCE.md',
    ROOT/'provenance/04_PROVENANCE_POLICY.md',
])
PUBLIC_CRITIQUE_FILES=require_public_files([
    ROOT/'critiques/00_CRITIQUE_PROTOCOL.md',
    ROOT/'critiques/01_ANTI_FALLACY_ARMOR.md',
    ROOT/'critiques/02_OPEN_CHALLENGE.md',
    ROOT/'critiques/03_WEEKLY_REFINEMENT_PROTOCOL.md',
    ROOT/'audit/00_DEEP_AUDIT_CHECKLIST.md',
    ROOT/'audit/01_AUDIT_ISSUE_TEMPLATE.md',
    ROOT/'audit/02_V0_2_PREFLIGHT_FINDINGS.md',
])

# Clean generated site to prevent stale pages.
if SITE.exists(): shutil.rmtree(SITE)
SITE.mkdir(exist_ok=True)
for d in ['assets/css','assets/js','machine','claims','assets']:
    (SITE/d).mkdir(parents=True,exist_ok=True)
shutil.copy(ROOT/'assets/css/main.css',SITE/'assets/css/main.css')
shutil.copy(ROOT/'assets/js/site.js',SITE/'assets/js/site.js')

content=sorted((ROOT/'content').glob('*.md'))
intro=home_body()
write_page('index.html',CFG['seo']['title'],intro,desc='BL∞ — hệ nghiên cứu mở do Lâm Kim Bách (Bách Lâm) khởi phát, về quan sát hữu hạn, không gian khả năng, Giả tại, provenance, phản biện và tri thức máy đọc được.')
write_page('theory.html','BL∞ — Học thuyết canonical',render_docs([p for p in content if p.name!='00_README_FIRST.md'],'BL∞ — Học thuyết canonical'),desc='Bản học thuyết canonical BL∞: Mệnh đề Vô hạn Bách Lâm, quan hệ Thực tại–Giả tại, giới hạn quan sát, khả đạt, phản biện và các cấu kiện đã nối phả hệ.')
bl_adn_source=(ROOT/'BL-ADN.md').read_text(encoding='utf-8')
write_page('bl-adn.html','BL-ADN — Giao thức Phả hệ Tri thức','<h1>BL-ADN — Giao thức Phả hệ Tri thức</h1>'+shift_headings(md(bl_adn_source)),desc='Giao thức Đóng dấu ADN Bách Lâm ∞ và Nối tiếp Phả hệ Tri thức, phiên bản 0.2.0.')
write_page('languages.html','BL∞ — Ngôn ngữ & phạm vi bản dịch',language_hub_body(),desc='Chọn ngôn ngữ của BL∞ và xem rõ phạm vi: tiếng Việt canonical, English core research edition và 11 bản khám phá Dân chủ Học thuật chưa duyệt đầy đủ.',comments=False)
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
    js=schema_generic(f'{cid} claim — {c["title"]}',url,desc,typ='CreativeWork',identifier=cid,extra={
        'text':c['statement'],'creativeWorkStatus':c['status'],
        'about':{'@type':'Thing','name':c.get('scope','BL∞')}
    })
    write_page(dest,f'{cid} claim — {c["title"]} | BL∞',body,desc=desc,base='../../',jsonld=js)
    claim_index.append({'id':cid,'title':c['title'],'type':c['type'],'status':c['status'],'url':url,'depends_on':deps,'novelty_dimensions':c.get('novelty_dimensions',[])})
rows.append('</div>')
write_page('claims.html','BL∞ — Claim Registry','\n'.join(rows),desc='Sổ đăng ký 68 claim BL∞ với ID, loại, trạng thái, dependency, phạm vi và điều kiện bác bỏ để người và máy có thể kiểm tra từng mệnh đề.')

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
    js=schema_generic(f'{code} asset — {a["name"]}',url,desc,typ='CreativeWork',identifier=code)
    write_page(dest,f'{code} asset — {a["name"]} | BL∞',body,desc=desc,base='../../',jsonld=js)
    asset_index.append({**a,'url':url})
arows.append('</div>')
write_page('assets.html','BL∞ — Asset & Technology Registry','\n'.join(arows),desc='Sổ cấu kiện BL∞: học thuyết, nguyên lý, giao thức, cơ chế và công nghệ có định danh, quan hệ, trạng thái và provenance riêng.')

write_page('provenance.html','BL∞ — Provenance',render_docs(PUBLIC_PROVENANCE_FILES,'BL∞ — Provenance'),desc='Nguồn gốc, phả hệ, vai trò tác giả và formalization của BL∞; phân biệt quan hệ, tác quyền, ưu tiên lịch sử và trạng thái kiểm chứng.')
write_page('critique.html','BL∞ — Giao thức phản biện',render_docs(PUBLIC_CRITIQUE_FILES,'BL∞ — Giao thức phản biện'),desc='Giao thức phản biện công khai BL∞: nêu đúng Claim ID, tiền đề, bước suy luận, countermodel, evidence hoặc xung đột provenance để hệ có thể sửa.')
write_page('machine.html','BL∞ — Machine Layer',md((ROOT/'machine/README.md').read_text(encoding='utf-8')),desc='Các giao diện máy đọc được của BL∞: manifest, claim graph, asset index, topology, provenance, translation status và chính sách công khai BL-CPR.')

# Machine layer
manifest={
  'namespace':'BL∞','canonical_name':CFG['project']['canonical_name_en'],'canonical_name_vi':CFG['project']['canonical_name_vi'],
  'creator':CFG['project']['author'],'aliases':CFG['project']['aliases'],'version':CFG['project']['version'],
  'canonical_url':CFG['project']['canonical_url'],'repository':CFG['project']['repository'],'date_created':CFG['project'].get('date_created',CFG['project']['date']),'date_released':CFG['project']['date'],'last_updated':CFG['project'].get('last_updated',CFG['project']['date']),
  'claim_registry':'claims.json','claim_index':'claim-index.json','claim_graph':'claim-graph.jsonld',
  'asset_registry':'assets.json','asset_index':'asset-index.json','novelty_ontology':'novelty-ontology.json','logic_stack':'logic-stack.json','historical_graph':'historical-graph.jsonld',
  'disclosure_policy':'disclosure-policy.json','bl_adn_protocol':'../bl-adn.html','bl_adn_source':'../bl-adn.md','author_profile':'../author.html','language_hub':'../languages.html','translation_index':'../translations/translation-index.json','translation_status':'translation-status.json','academic_democracy_discovery':'academic-democracy-discovery.json','reverse_system':'bl-reverse-system.json','hypothetical_reality_doctrine':'bl-hrd.json','unified_system':'bl-infinity-unified-system.json','constituent_registry':'unified-constituents.json','reality_gia_tai_topology':'reality-gia-tai-topology.json','machine_greeting':'welcome.txt','translation_pack':'../translations/greeting.multilingual.md','llms':'../llms.txt','feed':'../feed.xml','content_hash':None
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
urls=['','theory.html','bl-adn.html','claims.html','assets.html','languages.html','provenance.html','critique.html','machine.html']
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
release_dt=datetime.datetime.fromisoformat(CFG['project'].get('last_updated',CFG['project']['date'])).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
pub_date=release_dt.strftime('%a, %d %b %Y %H:%M:%S %z')
rss=f'''<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>BL∞ updates</title><link>{CFG['project']['canonical_url']}</link><description>{CFG['seo']['description']}</description><lastBuildDate>{pub_date}</lastBuildDate><item><title>BL∞ {CFG['project']['version']}</title><link>{CFG['project']['canonical_url']}</link><guid>{CFG['project']['canonical_url']}#{CFG['project']['version']}</guid><pubDate>{pub_date}</pubDate></item></channel></rss>'''
(SITE/'feed.xml').write_text(rss,encoding='utf-8')

# GitHub Pages 404 keeps navigation usable.
project_base='/'+CFG['project']['canonical_url'].split('/',3)[-1].strip('/')+'/'
body404=f'<h1>Không tìm thấy object</h1><p>URL này không tồn tại ở version hiện tại. Hãy quay về <a href="{project_base}index.html">BL∞</a> hoặc <a href="{project_base}claims.html">Claim Registry</a>.</p>'
write_page('404.html','BL∞ — Không tìm thấy',body404,base=project_base,comments=False,robots='noindex,follow')
print(f'Built {SITE}: {len(CLAIMS["claims"])} claim pages, {len(ASSETS["assets"])} asset pages')
