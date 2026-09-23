from __future__ import annotations
import argparse, glob, json, os
from collections import Counter


def board_of(ev):
    b = ev.get('board')
    if isinstance(b, list) and b and isinstance(b[0], list):
        return b
    return None


def dims(b):
    return (len(b), len(b[0]) if b else 0)


def changed_cells(a,b):
    if not a or not b or dims(a)!=dims(b): return []
    out=[]
    for r in range(len(a)):
        for c in range(len(a[0])):
            if a[r][c] != b[r][c]: out.append((r,c,a[r][c],b[r][c]))
    return out


def bbox(cells):
    if not cells: return None
    rs=[x[0] for x in cells]; cs=[x[1] for x in cells]
    return [min(rs),min(cs),max(rs),max(cs)]


def comps_nonzero(b):
    if not b: return []
    H,W=dims(b); seen=set(); out=[]
    for r in range(H):
        for c in range(W):
            if b[r][c] in (0,'0',None) or (r,c) in seen: continue
            val=b[r][c]; stack=[(r,c)]; seen.add((r,c)); pts=[]
            while stack:
                x,y=stack.pop(); pts.append((x,y))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=x+dx,y+dy
                    if 0<=nx<H and 0<=ny<W and (nx,ny) not in seen and b[nx][ny]==val:
                        seen.add((nx,ny)); stack.append((nx,ny))
            out.append({'value':val,'n':len(pts),'bbox':bbox([(r,c,None,None) for r,c in pts])})
    out.sort(key=lambda x:(x['bbox'],str(x['value'])))
    return out


def compact_ascii(ev, max_rows=80, max_cols=160):
    s=ev.get('board_ascii')
    if isinstance(s,str):
        lines=s.splitlines()[:max_rows]
        return '\n'.join(line[:max_cols] for line in lines)
    b=board_of(ev)
    if not b:return ''
    return '\n'.join(' '.join(map(str,row[:max_cols])) for row in b[:max_rows])


def load(path):
    arr=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: arr.append(json.loads(line))
    return arr


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args()
    paths=sorted(glob.glob(os.path.join(args.root,'tr87-cd924810_p[0-4]_events.jsonl')))
    assert len(paths)==5, paths
    report={'files':[], 'truth_boundary':'PUBLIC_SOURCEFREE_RAW_P0P4_INSPECTION_ONLY'}
    preview=[]
    for p in paths:
        evs=load(p); boards=[board_of(e) for e in evs]
        valid=[b for b in boards if b]
        acts=Counter(str(e.get('action_name') or e.get('action') or e.get('event_type') or '') for e in evs)
        trans=[]
        prev=None
        for i,e in enumerate(evs):
            b=board_of(e)
            if b and prev:
                ch=changed_cells(prev,b)
                if ch:
                    trans.append({'i':i,'action':e.get('action_name') or e.get('action'),'n_changed':len(ch),'bbox':bbox(ch),'value_pairs':Counter((str(x[2]),str(x[3])) for x in ch).most_common(12)})
            if b: prev=b
        initial=valid[0] if valid else None
        ent={'file':os.path.basename(p),'records':len(evs),'board_dims':dims(initial) if initial else None,'action_counts':dict(acts),'changed_transitions':trans[:80],'initial_nonzero_components':comps_nonzero(initial)[:200] if initial else []}
        report['files'].append(ent)
        preview.append(f"===== {os.path.basename(p)} INITIAL =====\n{compact_ascii(next(e for e in evs if board_of(e)))}\n")
    with open(args.out,'w',encoding='utf-8') as f: json.dump(report,f,indent=2,sort_keys=True)
    with open(os.path.splitext(args.out)[0]+'_preview.txt','w',encoding='utf-8') as f: f.write('\n'.join(preview))
    print(json.dumps({'files':len(paths),'records':sum(x['records'] for x in report['files']),'output':args.out},sort_keys=True))

if __name__=='__main__': main()
