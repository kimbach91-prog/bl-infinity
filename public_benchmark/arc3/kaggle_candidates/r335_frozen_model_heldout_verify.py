from __future__ import annotations
import argparse, glob, hashlib, json, os
from collections import Counter

PHASE_PLUS='ACTION1'; PHASE_MINUS='ACTION2'; CURSOR_LEFT='ACTION3'; CURSOR_RIGHT='ACTION4'


def read_jsonl(path):
    rows=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: rows.append(json.loads(line))
    return rows


def ascii_board(event):
    s=event.get('board_ascii')
    return s.splitlines() if isinstance(s,str) else None


def normalize(points):
    points=sorted(set((int(r),int(c)) for r,c in points))
    if not points:return ()
    r0=min(r for r,c in points); c0=min(c for r,c in points)
    return tuple(sorted((r-r0,c-c0) for r,c in points))


def canonical_glyph(points):
    if not points:return ()
    variants=[]
    for reflect in (False,True):
        for turns in range(4):
            out=[]
            for r,c in points:
                x,y=r,c
                for _ in range(turns): x,y=y,-x
                if reflect:y=-y
                out.append((x,y))
            variants.append(normalize(out))
    return min(variants)


def glyph_id(points):
    tok=canonical_glyph(points)
    return hashlib.sha256(json.dumps(tok,separators=(',',':')).encode()).hexdigest()[:16]


def locate_panels(lines):
    if not lines:return []
    H=len(lines); W=min(len(x) for x in lines); found=[]
    for r in range(max(0,H-6)):
        for c in range(max(0,W-6)):
            label=lines[r][c]
            if label not in ('S','P'):continue
            if not all(lines[r][c+j]==label and lines[r+6][c+j]==label for j in range(7)):continue
            if not all(lines[r+i][c]==label and lines[r+i][c+6]==label for i in range(1,6)):continue
            pts=[(i-1,j-1) for i in range(1,6) for j in range(1,6) if lines[r+i][c+j]=='B']
            if not pts:continue
            found.append({'r':r,'c':c,'kind':label,'id':glyph_id(pts)})
    return found


def parse_state(event):
    lines=ascii_board(event)
    panels=locate_panels(lines)
    if not panels:return None
    byrow={}
    for p in panels: byrow.setdefault(p['r'],[]).append(p)
    relation=[]; source=[]; editable=[]
    for r,row in byrow.items():
        row=sorted(row,key=lambda p:p['c']); kinds=''.join(p['kind'] for p in row)
        if kinds=='SPSP': relation.extend(((row[0],row[1]),(row[2],row[3])))
        elif kinds=='SSSSS': source=row
        elif kinds=='PPPPP': editable=row
    if len(relation)!=6 or len(source)!=5 or len(editable)!=5:return None
    relation_map={}
    for s,p in relation:
        if s['id'] in relation_map and relation_map[s['id']]!=p['id']:return None
        relation_map[s['id']]=p['id']
    if len(relation_map)!=6:return None
    targets=[]
    for s in source:
        if s['id'] not in relation_map:return None
        targets.append(relation_map[s['id']])
    centers=[p['c']+3 for p in editable]
    white_cols=[]
    if lines:
        for line in lines:
            for c,ch in enumerate(line):
                if ch=='W':white_cols.append(c)
    cursor=None
    if white_cols:
        m=sum(white_cols)/len(white_cols)
        ds=sorted((abs(m,c0),i) for i,c0 in enumerate(centers))
        if len(ds)==1 or ds[0][0]<ds[1][0]:cursor=ds[0][1]
    return {'current':[p['id'] for p in editable],'target':targets,'cursor':cursor,'relation_map':relation_map}


def inverse_edges(cycle):
    return {cycle[(i+1)%len(cycle)]:cycle[i] for i in range(len(cycle))}


def verify_trace(rows, cycle, cursor_rule):
    next_phase={cycle[i]:cycle[(i+1)%len(cycle)] for i in range(len(cycle))}; prev_phase=inverse_edges(cycle)
    checked=predicted=correct=abstain=0; mismatch=[]; parsed=0
    prev_event=None; prev_state=None
    for i,event in enumerate(rows):
        st=parse_state(event)
        if st is not None:parsed+=1
        if prev_event is not None and event.get('type')=='action':
            action=event.get('action_name')
            if action in (PHASE_PLUS,PHASE_MINUS,CURSOR_LEFT,CURSOR_RIGHT) and not event.get('game_over'):
                checked+=1
                a=prev_state if prev_state is not None else parse_state(prev_event); b=st
                if a is None or b is None:
                    abstain+=1
                elif action in (PHASE_PLUS,PHASE_MINUS):
                    pos=a['cursor']
                    if pos is None or b['cursor']!=pos:
                        predicted+=1; mismatch.append({'i':i,'reason':'cursor_not_stable','action':action})
                    else:
                        dif=[j for j,(x,y) in enumerate(zip(a['current'],b['current'])) if x!=y]
                        if dif!=[pos]:
                            predicted+=1; mismatch.append({'i':i,'reason':'not_single_edit_at_cursor','action':action,'diff':dif,'cursor':pos})
                        else:
                            expected=(next_phase if action==PHASE_PLUS else prev_phase).get(a['current'][pos])
                            if expected is None:abstain+=1
                            else:
                                predicted+=1
                                if expected==b['current'][pos]:correct+=1
                                else:mismatch.append({'i':i,'reason':'phase_mismatch','action':action,'expected':expected,'actual':b['current'][pos]})
                else:
                    if a['cursor'] is None or b['cursor'] is None:abstain+=1
                    elif a['current']!=b['current']:
                        predicted+=1; mismatch.append({'i':i,'reason':'cursor_action_mutated_editable','action':action})
                    else:
                        expected_delta=cursor_rule[action]
                        predicted+=1
                        if (b['cursor']-a['cursor'])%5==expected_delta:correct+=1
                        else:mismatch.append({'i':i,'reason':'cursor_delta_mismatch','action':action,'before':a['cursor'],'after':b['cursor'],'expected_delta':expected_delta})
        prev_event=event
        if st is not None:prev_state=st
    return {'records':len(rows),'parsed_states':parsed,'checked':checked,'predicted':predicted,'correct':correct,'mismatch_count':len(mismatch),'abstain':abstain,
            'accuracy':correct/predicted if predicted else None,'coverage':predicted/checked if checked else None,'mismatches':mismatch[:20]}


def plan_from_initial(st, cycle, cursor_rule):
    if st is None or st['cursor'] is None:return {'exists':False,'reason':'unparsed_initial'}
    idx={x:i for i,x in enumerate(cycle)}
    if any(x not in idx for x in st['current']+st['target']):return {'exists':False,'reason':'token_outside_frozen_cycle'}
    if cursor_rule.get(CURSOR_RIGHT)!=1:return {'exists':False,'reason':'right_cursor_not_plus1'}
    cur=list(st['current']); cursor=st['cursor']; actions=[]; offsets=[]
    for step in range(5):
        site=(st['cursor']+step)%5
        if cursor!=site:return {'exists':False,'reason':'cursor_plan_invariant'}
        f=(idx[st['target'][site]]-idx[cur[site]])%len(cycle); b=f-len(cycle); d=b if abs(b)<abs(f) else f
        offsets.append(d)
        if d>=0:
            for _ in range(d):cur[site]=cycle[(idx[cur[site]]+1)%len(cycle)];actions.append(PHASE_PLUS)
        else:
            for _ in range(-d):cur[site]=cycle[(idx[cur[site]]-1)%len(cycle)];actions.append(PHASE_MINUS)
        if step<4:cursor=(cursor+1)%5;actions.append(CURSOR_RIGHT)
    return {'exists':cur==st['target'],'final_matches_target':cur==st['target'],'n_actions':len(actions),'under_128':len(actions)<128,'offsets':offsets,'actions':actions}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--model',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    with open(args.model,'r',encoding='utf-8') as f:model=json.load(f)
    cycle=model['phase_cycle']; cursor_rule=model['cursor_delta_mod5']
    paths=sorted(glob.glob(os.path.join(args.root,'tr87-cd924810_p[5-9]_events.jsonl')))
    assert len(paths)==5,paths
    results=[]
    for p in paths:
        rows=read_jsonl(p); vr=verify_trace(rows,cycle,cursor_rule); plan=plan_from_initial(parse_state(rows[0]),cycle,cursor_rule)
        results.append({'file':os.path.basename(p),'verification':vr,'plan':plan})
    checked=sum(x['verification']['checked'] for x in results);pred=sum(x['verification']['predicted'] for x in results);cor=sum(x['verification']['correct'] for x in results);absn=sum(x['verification']['abstain'] for x in results)
    plan_count=sum(bool(x['plan'].get('exists') and x['plan'].get('under_128')) for x in results)
    report={'truth_boundary':'PUBLIC_SOURCEFREE_P5P9_FROZEN_NO_RETRAIN_HELDOUT_ONLY','model_source':model,'results':results,
            'aggregate':{'checked':checked,'predicted':pred,'correct':cor,'abstain':absn,'mismatch_count':pred-cor,'accuracy':cor/pred if pred else None,'coverage':pred/checked if checked else None,'safe_plan_exists_traces':plan_count,'total_traces':5},
            'historical_leakage_note':'p5-p9 had prior source-assisted study elsewhere in the job; this verifier uses only the frozen p0-p4 action model and raw source-free p5-p9 traces, with no model update. Treat as stronger source-free confirmation, not pristine globally unseen data.',
            'promotion_boundary':'representation/action-mechanism heldout only; no whole-game/Kaggle promotion without positive terminal/provider receipts'}
    with open(args.out,'w',encoding='utf-8') as f:json.dump(report,f,indent=2,sort_keys=True)
    print(json.dumps(report['aggregate'],sort_keys=True))

if __name__=='__main__':main()
