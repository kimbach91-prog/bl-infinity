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
try: historical=json.loads((ROOT/'machine/historical-graph.jsonld').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'historical graph: {e}'); historical={}
try: logic_stack=json.loads((ROOT/'machine/logic-stack.json').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'logic stack: {e}'); logic_stack={}
try: entity_graph=json.loads((ROOT/'machine/graph.jsonld').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'entity graph: {e}'); entity_graph={}

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

# Historical truth boundary: chronology is separate from logic/dependency.
if historical.get('graphType') != 'HISTORICAL_GRAPH':
    errors.append('historical graph missing graphType=HISTORICAL_GRAPH')
h_nodes={n.get('@id'):n for n in historical.get('@graph',[]) if isinstance(n,dict)}
blok_event=h_nodes.get('bl:event-blok-foundational-nucleus',{})
if blok_event.get('precedes') != 'bl:event-optimizer-essence-chain':
    errors.append('historical graph must preserve owner-confirmed BLOK -> PRECEDES -> Optimizer/Essence edge')
if blok_event.get('exactDateKnown') is not False:
    errors.append('BLOK foundational nucleus absolute date must remain unresolved')
logic_graph_type=logic_stack.get('graph_type')
allowed_logic_types={'LOGICAL_GRAPH_VIEW','DYNAMIC_LOGICAL_GRAPH_VIEW','DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW'}
if logic_graph_type not in allowed_logic_types or logic_stack.get('not_chronology') is not True:
    errors.append('logic stack must declare an approved logical/dynamic/open-ended graph view and not_chronology=true')
if logic_graph_type in {'DYNAMIC_LOGICAL_GRAPH_VIEW','DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW'}:
    if logic_stack.get('not_fixed_hierarchy') is not True:
        errors.append('dynamic logic stack must declare not_fixed_hierarchy=true')
    if 'THUC_DINH' not in logic_stack.get('mode_cycles',{}) or 'GIA_DINH' not in logic_stack.get('mode_cycles',{}):
        errors.append('dynamic logic stack must expose THUC_DINH and GIA_DINH mode cycles')
if logic_graph_type == 'DYNAMIC_OPEN_ENDED_LOGICAL_GRAPH_VIEW':
    if logic_stack.get('not_exhaustive_taxonomy') is not True:
        errors.append('open-ended logic stack must declare not_exhaustive_taxonomy=true')
    for mode in ['UNKNOWN_DISCOVERY','MIXED_CONTESTED']:
        if mode not in logic_stack.get('mode_cycles',{}):
            errors.append(f'open-ended logic stack missing mode cycle {mode}')
    if logic_stack.get('open_ended_phase_space') != 'open-ended-epistemic-phase-space.json':
        errors.append('open-ended logic stack missing phase-space machine pointer')
if logic_stack.get('historical_graph') != 'historical-graph.jsonld':
    errors.append('logic stack missing historical graph pointer')

public_provenance_path=ROOT/'provenance/00_PUBLIC_PROVENANCE.md'
if not public_provenance_path.exists():
    errors.append('missing sanitized public provenance interface')
else:
    public_provenance=public_provenance_path.read_text(encoding='utf-8')
    public_provenance_lower=public_provenance.lower()
    for marker in ['sanitized_public_provenance','blok foundational nucleus','precedes','relative order only','unknown','ai formalization != author verbatim quote']:
        if marker not in public_provenance_lower:
            errors.append(f'public provenance missing boundary marker: {marker}')

# Public repository must not reintroduce detailed/private lineage artifacts.
for forbidden in [
    ROOT/'handoff',
    ROOT/'provenance/raw',
    ROOT/'provenance/private',
]:
    if forbidden.exists():
        errors.append(f'protected provenance/runtime path exists in public tree: {forbidden.relative_to(ROOT)}')

e_nodes={n.get('@id'):n for n in entity_graph.get('@graph',[]) if isinstance(n,dict)}
for required_entity in ['bl:blok','bl:optimizer','bl:bl-infinity','bl:bl-aegis']:
    if required_entity not in e_nodes: errors.append(f'entity graph missing independent BL-lineage object {required_entity}')
if e_nodes.get('bl:bl-aegis',{}).get('isPartOf') == {'@id':'bl:bl-infinity'}:
    errors.append('entity graph must not collapse BL-AEGIS into BL-infinity via historical overreach')

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

result={'errors':errors,'warnings':sorted(set(warnings)),'notes':notes,'claims':len(ids),'assets':len(aset),'version':cfg.get('project',{}).get('version')}
print(json.dumps(result,ensure_ascii=False,indent=2))
if errors: sys.exit(1)
