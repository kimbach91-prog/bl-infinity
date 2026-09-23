from __future__ import annotations
import argparse, glob, hashlib, json, os
from collections import Counter, defaultdict

FIELDS=('action_num','analysis_step','action_name','action_display','level','score','reward','state','done','game_over','level_completed','run_complete','run_status','board_changed','type','batch_index','batch_size')


def load(path):
    out=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: out.append(json.loads(line))
    return out


def board_of(e):
    b=e.get('board')
    return b if isinstance(b,list) and b and isinstance(b[0],list) else None


def ascii_lines(e):
    s=e.get('board_ascii')
    if isinstance(s,str): return s.splitlines()
    return []


def crop(e,r0=39,r1=63,c0=8,c1=57):
    lines=ascii_lines(e)
    return '\n'.join(x[c0:c1] for x in lines[r0:r1]) if lines else ''


def slim(e):
    return {k:e.get(k) for k in FIELDS if k in e}


def core(e):
    return tuple(e.get(k) for k in ('level','score','reward','state','done','game_over','level_completed','run_complete','run_status'))


def board_sig(e):
    b=board_of(e)
    if not b:return None
    return hashlib.sha256(json.dumps(b,separators=(',',':')).encode()).hexdigest()[:20]


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args()
    paths=sorted(glob.glob(os.path.join(a.root,'tr87-cd924810_p[0-4]_events.jsonl')))
    assert len(paths)==5, paths
    report={'truth_boundary':'PUBLIC_SOURCEFREE_P0P4_TERMINAL_SIGNAL_ONLY','files':[]}
    for p in paths:
        evs=load(p)
        counts={k:Counter() for k in ('level','score','reward','state','done','game_over','level_completed','run_complete','run_status')}
        for e in evs:
            for k,c in counts.items(): c[repr(e.get(k))]+=1
        changes=[]; prev=None
        for i,e in enumerate(evs):
            c=core(e)
            action=e.get('action_name') or ''
            if prev is None or c!=prev or action=='RESET' or bool(e.get('game_over')) or bool(e.get('level_completed')) or bool(e.get('run_complete')) or (e.get('reward') not in (None,0,0.0)) or (e.get('score') not in (None,0,0.0)):
                changes.append({'i':i,'event':slim(e),'board_sig':board_sig(e),'work_crop':crop(e)})
            prev=c
        # exact action runs between reset boundaries, without transcripts
        episodes=[]; cur=[]; start=0
        for i,e in enumerate(evs):
            if e.get('type')=='action':
                act=e.get('action_name')
                if act=='RESET' and cur:
                    episodes.append({'start_i':start,'end_i':i-1,'actions':cur})
                    cur=[]; start=i
                cur.append({'i':i,'action':act,'action_num':e.get('action_num'),'state':e.get('state'),'score':e.get('score'),'reward':e.get('reward'),'game_over':e.get('game_over'),'level_completed':e.get('level_completed'),'run_complete':e.get('run_complete')})
        if cur: episodes.append({'start_i':start,'end_i':len(evs)-1,'actions':cur})
        # summarize each episode only
        eps=[]
        for ep in episodes:
            acts=ep['actions']
            eps.append({
                'start_i':ep['start_i'],'end_i':ep['end_i'],'n_actions':len(acts),
                'action_counts':dict(Counter(x['action'] for x in acts)),
                'last_action':acts[-1] if acts else None,
                'positive_events':[x for x in acts if (x['score'] or 0)>0 or (x['reward'] or 0)>0 or x['level_completed'] or x['run_complete']],
                'game_over_events':[x for x in acts if x['game_over']],
            })
        report['files'].append({'file':os.path.basename(p),'records':len(evs),'value_counts':{k:dict(v) for k,v in counts.items()},'status_changes':changes,'episodes':eps})
    with open(a.out,'w',encoding='utf-8') as f: json.dump(report,f,indent=2,sort_keys=True)
    brief=[]
    for x in report['files']:
        brief.append({'file':x['file'],'records':x['records'],'value_counts':x['value_counts'],'episodes':x['episodes']})
    print(json.dumps({'files':brief},sort_keys=True))

if __name__=='__main__': main()
