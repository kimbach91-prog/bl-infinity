from pathlib import Path
import argparse,json,re,sys,yaml
from collections import defaultdict, deque
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--strict',action='store_true',help='fail on structural/epistemic validation errors')
parser.add_argument('--release',action='store_true',help='also fail on deployment placeholders')
args=parser.parse_args()
errors=[]; warnings=[]; notes=[]

try: cfg=yaml.safe_load((ROOT/'bl.config.yml').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'config: {e}'); cfg={}
try: data=json.loads((ROOT/'claims/claims.json').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'claims json: {e}'); data={'claims':[]}
try: assets=json.loads((ROOT/'machine/assets.json').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'assets json: {e}'); assets={'assets':[]}

ids=set(); allowed={'axiom','definition','theorem','proposition','conjecture','method','protocol','empirical-interface','analogy','principle','relation','model','mechanism','effect','theorem-schema'}
claims=data.get('claims',[])
for c in claims:
    cid=c.get('id')
    if not cid: errors.append('claim missing id'); continue
    if cid in ids: errors.append(f'duplicate claim id {cid}')
    ids.add(cid)
    if c.get('type') not in allowed: errors.append(f'{cid}: invalid type {c.get("type")}')
    for f in ['title','statement','status','scope','falsifier']:
        if not c.get(f): errors.append(f'{cid}: missing {f}')
    if c.get('type') in {'theorem','theorem-schema'} and c.get('status') not in {'formal','formalizable'}:
        warnings.append(f'{cid}: theorem-like claim has status {c.get("status")}')
    if c.get('status') in {'proposed','conjectural','open','optional-speculative'} and not c.get('falsifier'):
        errors.append(f'{cid}: open/proposed claim missing attack surface')
for c in claims:
    for d in c.get('depends_on',[]):
        if d not in ids: errors.append(f'{c["id"]}: unknown dependency {d}')

# Directed dependency cycle check.
g={c['id']:list(c.get('depends_on',[])) for c in claims if c.get('id')}
WHITE,GRAY,BLACK=0,1,2; color={n:WHITE for n in g}; stack=[]
def dfs(n):
    color[n]=GRAY; stack.append(n)
    for d in g.get(n,[]):
        if d not in g: continue
        if color[d]==GRAY:
            i=stack.index(d) if d in stack else 0
            errors.append('claim dependency cycle: '+' -> '.join(stack[i:]+[d])); continue
        if color[d]==WHITE: dfs(d)
    stack.pop(); color[n]=BLACK
for n in list(g):
    if color[n]==WHITE: dfs(n)

# Asset uniqueness/dependencies and cycles. Dependencies may refer to legacy asset codes not yet in machine registry -> warning.
a_codes=[]; aset=set()
for a in assets.get('assets',[]):
    code=a.get('code')
    if not code: errors.append('asset missing code'); continue
    if code in aset: errors.append(f'duplicate asset code {code}')
    aset.add(code); a_codes.append(code)
    for f in ['name','kind','status']:
        if not a.get(f): errors.append(f'{code}: asset missing {f}')
for a in assets.get('assets',[]):
    for d in a.get('dependencies',[]):
        if d not in aset: warnings.append(f'{a["code"]}: asset dependency {d} not in machine asset registry')
ag={a['code']:[d for d in a.get('dependencies',[]) if d in aset] for a in assets.get('assets',[]) if a.get('code')}
acolor={n:WHITE for n in ag}; astack=[]
def adfs(n):
    acolor[n]=GRAY; astack.append(n)
    for d in ag.get(n,[]):
        if acolor[d]==GRAY:
            i=astack.index(d) if d in astack else 0
            errors.append('asset dependency cycle: '+' -> '.join(astack[i:]+[d])); continue
        if acolor[d]==WHITE: adfs(d)
    astack.pop(); acolor[n]=BLACK
for n in list(ag):
    if acolor[n]==WHITE: adfs(n)

# Canonical content guardrails against self-sealing/priority overclaim.
joined='\n'.join(p.read_text(encoding='utf-8') for p in (ROOT/'content').glob('*.md'))
for phrase in ['đã chứng minh mọi giả thuyết đều có thật','không thể phản bác theo định nghĩa','AI đồng ý nên đúng','không ai trong lịch sử từng nghĩ']:
    if phrase.lower() in joined.lower(): errors.append(f'forbidden self-sealing/absolute formulation found: {phrase}')
if 'Prior art(component) không tự động là prior art(system)' not in joined:
    warnings.append('novelty ontology guardrail sentence missing')

# Required post-origin objects.
required_new={'BL-NCI','BL-CNO','BL-RNO','BL-SNO','BL-ANO','BL-FNO','BL-PNO','BL-ENO','BL-IDR','BL-NVM','BL-RDN','BL-NTO','BL-LSI','BL-ICV','BL-IRC','BL-IGR','BL-IFH','BL-FCR','BL-TNI','BL-SRS','BL-ICO','BL-PIRAL'}
missing=sorted(required_new-ids)
if missing: errors.append('missing v0.2 canonical claims: '+', '.join(missing))

# Deployment placeholders.
conftext=(ROOT/'bl.config.yml').read_text(encoding='utf-8') if (ROOT/'bl.config.yml').exists() else ''
placeholder=[]
if 'YOUR-DOMAIN.example' in conftext: placeholder.append('canonical domain')
if 'YOUR_GITHUB_USERNAME' in conftext: placeholder.append('GitHub username/repository')
if placeholder:
    msg='deployment placeholders remain: '+', '.join(placeholder)
    if args.release: errors.append(msg)
    else: warnings.append(msg)

# Raw transcript boundary: reconstructed provenance must not masquerade as exact export.
raw=ROOT/'provenance/03_RAW_TRANSCRIPT_IMPORT.md'
if raw.exists() and 'import' in raw.read_text(encoding='utf-8').lower():
    warnings.append('exact raw transcript has not yet been imported/hashed; current provenance is structured reconstruction + selected excerpts')

result={'errors':errors,'warnings':sorted(set(warnings)),'notes':notes,'claims':len(ids),'assets':len(aset),'version':cfg.get('project',{}).get('version')}
print(json.dumps(result,ensure_ascii=False,indent=2))
if errors: sys.exit(1)
