from __future__ import annotations
import argparse, glob, hashlib, json, os
from collections import Counter, defaultdict

A1='ACTION1'; A2='ACTION2'; LEFT='ACTION3'; RIGHT='ACTION4'


def load(path):
    out=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: out.append(json.loads(line))
    return out


def lines_of(e):
    s=e.get('board_ascii')
    return s.splitlines() if isinstance(s,str) else []


def norm_coords(cells):
    pts=tuple(sorted(set(cells)))
    if not pts:return ()
    r0=min(r for r,c in pts); c0=min(c for r,c in pts)
    return tuple(sorted((r-r0,c-c0) for r,c in pts))


def d4(cells):
    pts=list(cells)
    if not pts:return ()
    variants=[]
    for k in range(8):
        out=[]
        for r,c in pts:
            x,y=r,c
            for _ in range(k%4): x,y=y,-x
            if k>=4:y=-y
            out.append((x,y))
        variants.append(norm_coords(out))
    return min(variants)


def token_id(tok):
    raw=json.dumps(tok,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def find_panels(lines):
    if not lines:return []
    H=len(lines); W=min(map(len,lines)); out=[]
    for r in range(H-6):
        for c in range(W-6):
            col=lines[r][c]
            if col not in ('S','P'):continue
            ok=True
            for j in range(7):
                if lines[r][c+j]!=col or lines[r+6][c+j]!=col:ok=False;break
            if not ok:continue
            for i in range(1,6):
                if lines[r+i][c]!=col or lines[r+i][c+6]!=col:ok=False;break
            if not ok:continue
            cells=[(i-1,j-1) for i in range(1,6) for j in range(1,6) if lines[r+i][c+j]=='B']
            if not cells:continue
            tok=d4(cells)
            out.append({'r':r,'c':c,'color':col,'tok':tok,'id':token_id(tok),'black':len(cells)})
    return out


def layout(e):
    lines=lines_of(e); panels=find_panels(lines)
    if not panels:return None
    rows=sorted(set(p['r'] for p in panels))
    # Structural grammar expected: top relation rows each S,P,S,P; bottom two rows are 5x S then 5x P.
    rel=[]; input_slots=[]; edit_slots=[]
    for r in rows:
        row=sorted([p for p in panels if p['r']==r],key=lambda x:x['c'])
        colors=''.join(p['color'] for p in row)
        if colors=='SPSP':
            rel.extend([(row[0],row[1]),(row[2],row[3])])
        elif colors=='SSSSS': input_slots=row
        elif colors=='PPPPP': edit_slots=row
    if len(rel)!=6 or len(input_slots)!=5 or len(edit_slots)!=5:return None
    # exactly one relation per canonical S key
    mp={}
    for s,p in rel:
        if s['id'] in mp and mp[s['id']]!=p['id']:return None
        mp[s['id']]=p['id']
    if len(mp)!=6:return None
    targets=[]
    for s in input_slots:
        if s['id'] not in mp:return None
        targets.append(mp[s['id']])
    current=[p['id'] for p in edit_slots]
    centers=[p['c']+3 for p in edit_slots]
    # Cursor inferred from W glyph centroid and nearest editable-site center.
    ws=[]
    for r,line in enumerate(lines):
        for c,ch in enumerate(line):
            if ch=='W':ws.append((r,c))
    cursor=None
    if ws:
        mean_c=sum(c for r,c in ws)/len(ws)
        dist=sorted((abs(mean_c-c),i) for i,c in enumerate(centers))
        if len(dist)==1 or dist[0][0] < dist[1][0]: cursor=dist[0][1]
    return {'mapping':mp,'targets':targets,'current':current,'cursor':cursor,'centers':centers,
            'relation_pairs':[(s['id'],p['id']) for s,p in rel],
            'input_ids':[p['id'] for p in input_slots], 'edit_ids':current}


def action_transitions(evs):
    out=[]
    prev=None
    for i,e in enumerate(evs):
        if prev is not None and e.get('type')=='action':
            act=e.get('action_name')
            if act in (A1,A2,LEFT,RIGHT) and not e.get('game_over'):
                a=layout(prev); b=layout(e)
                if a and b:
                    out.append({'i':i,'action':act,'before':a,'after':b})
        prev=e
    return out


def learn_model(trace_sets):
    succ=defaultdict(Counter); pred=defaultdict(Counter)
    cursor_counts=Counter(); phase_obs=0; cursor_obs=0; scars=[]
    for evs in trace_sets:
        for t in action_transitions(evs):
            act=t['action']; a=t['before']; b=t['after']
            if act in (A1,A2):
                pos=a['cursor']
                if pos is None or b['cursor']!=pos: scars.append('phase_cursor_unstable'); continue
                dif=[j for j,(x,y) in enumerate(zip(a['current'],b['current'])) if x!=y]
                if dif!=[pos]:
                    scars.append('phase_edit_not_single_cursor_site'); continue
                x=a['current'][pos]; y=b['current'][pos]
                if act==A1: succ[x][y]+=1; pred[y][x]+=1
                else: succ[y][x]+=1; pred[x][y]+=1
                phase_obs+=1
            else:
                ca,cb=a['cursor'],b['cursor']
                if ca is None or cb is None: scars.append('cursor_missing');continue
                if a['current']!=b['current']: scars.append('cursor_action_mutated_editable');continue
                delta=(cb-ca)%5
                cursor_counts[(act,delta)]+=1; cursor_obs+=1
    # deterministic edges only
    edges={}
    for x,c in succ.items():
        if len(c)!=1: scars.append('nonunique_successor'); continue
        edges[x]=next(iter(c))
    for y,c in pred.items():
        if len(c)!=1: scars.append('nonunique_predecessor')
    # derive a unique closed cycle containing all learned nodes
    nodes=set(edges)|set(edges.values())
    cycle=None
    if nodes and all(x in edges for x in nodes):
        start=min(nodes); cur=start; seq=[]; seen=set()
        while cur not in seen and cur in edges:
            seen.add(cur); seq.append(cur); cur=edges[cur]
        if cur==start and seen==nodes: cycle=seq
    # deterministic cursor semantics
    cursor_rule={}
    for act in (LEFT,RIGHT):
        vals=Counter()
        for (a,d),n in cursor_counts.items():
            if a==act: vals[d]+=n
        if len(vals)==1: cursor_rule[act]=next(iter(vals))
        elif vals: scars.append('nonunique_cursor_delta_'+act)
    return {'edges':edges,'cycle':cycle,'cursor_rule':cursor_rule,'phase_obs':phase_obs,'cursor_obs':cursor_obs,'scars':sorted(set(scars))}


def verify_model(model, evs):
    checked=correct=abstain=0; phase_checked=phase_correct=cursor_checked=cursor_correct=0; mism=[]
    edges=model['edges']; cr=model['cursor_rule']
    for t in action_transitions(evs):
        act=t['action']; a=t['before']; b=t['after']; checked+=1
        if act in (A1,A2):
            phase_checked+=1; pos=a['cursor']
            if pos is None or b['cursor']!=pos: mism.append([t['i'],'cursor_unstable']); continue
            dif=[j for j,(x,y) in enumerate(zip(a['current'],b['current'])) if x!=y]
            if dif!=[pos]: mism.append([t['i'],'wrong_edit_site']); continue
            x=a['current'][pos]; y=b['current'][pos]
            pred=edges.get(x) if act==A1 else next((u for u,v in edges.items() if v==x),None)
            if pred is None: abstain+=1; continue
            if pred==y: correct+=1; phase_correct+=1
            else:mism.append([t['i'],act,x,y,pred])
        else:
            cursor_checked+=1
            if act not in cr: abstain+=1; continue
            ca,cb=a['cursor'],b['cursor']
            if ca is None or cb is None: mism.append([t['i'],'cursor_missing']);continue
            if a['current']!=b['current']: mism.append([t['i'],'cursor_mutated']);continue
            if (cb-ca)%5==cr[act]: correct+=1; cursor_correct+=1
            else:mism.append([t['i'],act,ca,cb,cr[act]])
    predicted=correct+len(mism)
    return {'checked':checked,'predicted':predicted,'correct':correct,'mismatch_count':len(mism),'abstain':abstain,
            'accuracy':(correct/predicted if predicted else None),'coverage':(predicted/checked if checked else None),
            'phase_checked':phase_checked,'phase_correct':phase_correct,'cursor_checked':cursor_checked,'cursor_correct':cursor_correct,
            'mismatches':mism[:20]}


def plan_exists(model, initial):
    cyc=model['cycle']; cr=model['cursor_rule']
    if not cyc or initial is None or initial['cursor'] is None:return {'exists':False,'reason':'missing_cycle_or_cursor'}
    if set(initial['current']+initial['targets'])-set(cyc):return {'exists':False,'reason':'token_outside_cycle'}
    if RIGHT not in cr or cr[RIGHT]!=1:return {'exists':False,'reason':'right_cursor_rule_not_plus1'}
    n=len(cyc); idx={x:i for i,x in enumerate(cyc)}
    state=list(initial['current']); cursor=initial['cursor']; actions=[]; offsets=[]
    # fixed generic strategy: edit current site, then cycle RIGHT through all sites exactly once.
    for step in range(5):
        site=(initial['cursor']+step)%5
        if cursor!=site:return {'exists':False,'reason':'cursor_strategy_internal'}
        cur=state[site]; tgt=initial['targets'][site]
        f=(idx[tgt]-idx[cur])%n; back=f-n
        delta=back if abs(back)<abs(f) else f
        offsets.append(delta)
        if delta>=0:
            for _ in range(delta): state[site]=model['edges'][state[site]]; actions.append(A1)
        else:
            inv={v:k for k,v in model['edges'].items()}
            for _ in range(-delta): state[site]=inv[state[site]]; actions.append(A2)
        if step<4:
            cursor=(cursor+cr[RIGHT])%5; actions.append(RIGHT)
    return {'exists':state==initial['targets'],'actions':actions,'n_actions':len(actions),'offsets':offsets,'cycle_len':n,
            'final_matches_target':state==initial['targets'],'under_128':len(actions)<128}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args(); paths=sorted(glob.glob(os.path.join(a.root,'tr87-cd924810_p[0-4]_events.jsonl')));assert len(paths)==5
    traces=[load(p) for p in paths]
    folds=[]
    for h in range(5):
        train=[traces[i] for i in range(5) if i!=h]
        model=learn_model(train)
        test=verify_model(model,traces[h])
        init=layout(traces[h][0])
        plan=plan_exists(model,init)
        folds.append({'heldout':os.path.basename(paths[h]),'model':{'cycle':model['cycle'],'cycle_len':len(model['cycle']) if model['cycle'] else None,'cursor_rule':model['cursor_rule'],'phase_obs':model['phase_obs'],'cursor_obs':model['cursor_obs'],'scars':model['scars']},'test':test,'plan':plan,'initial_layout':init})
    pred=sum(x['test']['predicted'] for x in folds); cor=sum(x['test']['correct'] for x in folds); chk=sum(x['test']['checked'] for x in folds)
    plans=sum(bool(x['plan'].get('exists') and x['plan'].get('under_128')) for x in folds)
    report={'truth_boundary':'PUBLIC_SOURCEFREE_P0P4_RELATIONAL_PHASE_LOTO_ONLY__NO_POSITIVE_TERMINAL_LABELS',
            'method':'generic bordered-panel relation extraction + D4 token identity + LOTO action-dynamics cycle/cursor model + unique plan-existence simulation',
            'files':[os.path.basename(p) for p in paths], 'folds':folds,
            'aggregate':{'checked':chk,'predicted':pred,'correct':cor,'accuracy':cor/pred if pred else None,'coverage':pred/chk if chk else None,'safe_plan_exists_folds':plans,'total_folds':5},
            'promotion_boundary':'representation/action-mechanism evidence only; cannot promote to whole-game solve because p0-p4 contain no success/score/level-completion event'}
    with open(a.out,'w',encoding='utf-8') as f:json.dump(report,f,indent=2,sort_keys=True)
    print(json.dumps(report['aggregate'],sort_keys=True))

if __name__=='__main__':main()
