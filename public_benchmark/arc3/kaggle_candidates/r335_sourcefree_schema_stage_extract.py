from __future__ import annotations
import argparse, glob, hashlib, json, os
from collections import Counter, defaultdict

OMIT_KEYS = {'board','board_ascii','frame','image','pixels'}
SCALAR = (str,int,float,bool,type(None))


def load(path):
    out=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: out.append(json.loads(line))
    return out


def board_of(ev):
    b=ev.get('board')
    return b if isinstance(b,list) and b and isinstance(b[0],list) else None


def scalar_view(obj, prefix='', depth=0):
    out={}
    if depth>3: return out
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in OMIT_KEYS: continue
            p=f'{prefix}.{k}' if prefix else str(k)
            if isinstance(v,SCALAR): out[p]=v
            elif isinstance(v,dict): out.update(scalar_view(v,p,depth+1))
            elif isinstance(v,list) and len(v)<=12 and all(isinstance(x,SCALAR) for x in v): out[p]=v
    return out


def ascii_board(ev):
    s=ev.get('board_ascii')
    if isinstance(s,str): return s.splitlines()
    b=board_of(ev)
    if not b: return []
    return [''.join(str(x)[0] for x in row) for row in b]


def crop(lines,r0,r1,c0,c1):
    return '\n'.join(line[c0:c1] for line in lines[r0:r1])


def board_sig(b):
    if not b:return None
    raw=json.dumps(b,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def changed_bbox(a,b):
    if not a or not b or len(a)!=len(b) or len(a[0])!=len(b[0]): return None,0,[]
    pts=[]; pairs=Counter()
    for r in range(len(a)):
        for c in range(len(a[0])):
            if a[r][c]!=b[r][c]:
                pts.append((r,c)); pairs[(str(a[r][c]),str(b[r][c]))]+=1
    if not pts:return None,0,[]
    rs=[p[0] for p in pts]; cs=[p[1] for p in pts]
    return [min(rs),min(cs),max(rs),max(cs)],len(pts),pairs.most_common(10)


def interesting_indices(evs):
    idx={0,len(evs)-1}
    for i,e in enumerate(evs):
        action=str(e.get('action_name') or e.get('action') or '')
        et=str(e.get('event_type') or e.get('type') or '')
        sv=scalar_view(e)
        joined=' '.join([action,et]+[f'{k}={v}' for k,v in sv.items()]).lower()
        if any(x in joined for x in ('reset','done','success','win','lose','score','reward','level','stage','game_over','terminated')):
            idx.add(i)
        if i<8 or i>=len(evs)-8: idx.add(i)
    # add points where scalar signature changes
    prev=None
    for i,e in enumerate(evs):
        cur=json.dumps(scalar_view(e),sort_keys=True,default=str)
        if prev is not None and cur!=prev:
            idx.add(i); idx.add(max(0,i-1))
        prev=cur
    return sorted(idx)[:160]


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args()
    paths=sorted(glob.glob(os.path.join(args.root,'tr87-cd924810_p[0-4]_events.jsonl')))
    assert len(paths)==5, paths
    report={'truth_boundary':'PUBLIC_SOURCEFREE_P0P4_SCHEMA_STAGE_EXTRACT_ONLY','source_files':[]}
    global_keys=Counter(); global_scalar_keys=Counter()
    for path in paths:
        evs=load(path)
        keyfreq=Counter(); scalarfreq=Counter(); actionfreq=Counter(); eventfreq=Counter()
        snapshots=[]; transitions=[]; prevb=None
        for i,e in enumerate(evs):
            keyfreq.update(e.keys()); global_keys.update(e.keys())
            sv=scalar_view(e); scalarfreq.update(sv.keys()); global_scalar_keys.update(sv.keys())
            action=str(e.get('action_name') or e.get('action') or '')
            actionfreq[action]+=1
            eventfreq[str(e.get('event_type') or e.get('type') or '')]+=1
            b=board_of(e)
            if b and prevb:
                bb,n,pairs=changed_bbox(prevb,b)
                if n:
                    transitions.append({'i':i,'action':action,'bbox':bb,'n_changed':n,'pairs':pairs,'scalars':sv})
            if b: prevb=b
        for i in interesting_indices(evs):
            e=evs[i]; lines=ascii_board(e); b=board_of(e)
            snapshots.append({
                'i':i,
                'scalars':scalar_view(e),
                'action':e.get('action_name') or e.get('action'),
                'event_type':e.get('event_type') or e.get('type'),
                'board_sig':board_sig(b),
                'top_examples_crop':crop(lines,3,30,8,57) if lines else '',
                'work_crop':crop(lines,39,63,8,57) if lines else '',
            })
        report['source_files'].append({
            'file':os.path.basename(path), 'records':len(evs),
            'key_frequency':dict(keyfreq), 'scalar_key_frequency':dict(scalarfreq),
            'action_frequency':dict(actionfreq), 'event_frequency':dict(eventfreq),
            'interesting_snapshots':snapshots,
            'changed_transitions':transitions[:140],
        })
    report['global_key_frequency']=dict(global_keys)
    report['global_scalar_key_frequency']=dict(global_scalar_keys)
    with open(args.out,'w',encoding='utf-8') as f: json.dump(report,f,indent=2,sort_keys=True,ensure_ascii=False)
    print(json.dumps({'files':len(paths),'records':sum(x['records'] for x in report['source_files']), 'scalar_keys':sorted(report['global_scalar_key_frequency'])},sort_keys=True))

if __name__=='__main__': main()
