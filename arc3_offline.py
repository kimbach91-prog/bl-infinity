#!/usr/bin/env python3
"""Public ARC3 acquisition and offline engine smoke; no competition submission.
Evaluator-only: never expose game source or metadata to a future solver.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, logging, os, platform, random, sys, time
from pathlib import Path
EXPECTED = set('tn36 lf52 cn04 bp35 wa30 lp85 r11l tu93 sp80 m0r0 vc33 ar25 ka59 sc25 sk48 dc22 cd82 ft09 g50t ls20 re86 s5i5 sb26 su15 tr87'.split())
def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def quiet():
    log = logging.getLogger('arc3-acquisition-private')
    log.handlers.clear(); log.addHandler(logging.NullHandler())
    log.propagate = False; log.disabled = True
    return log
def clean():
    for name in ('ARC_API_KEY','ARC_BASE_URL','OPERATION_MODE','ENVIRONMENTS_DIR'):
        os.environ.pop(name, None)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
def acquire(root):
    clean()
    from arc_agi import Arcade, OperationMode
    envdir = root/'environment_files'; envdir.mkdir(parents=True, exist_ok=True)
    arc = Arcade(arc_base_url='https://three.arcprize.org', operation_mode=OperationMode.NORMAL,
                 environments_dir=str(envdir), recordings_dir=str(root/'acquisition_records'), logger=quiet())
    catalog = sorted(arc.get_environments(), key=lambda e:e.game_id)
    ids = [e.game_id for e in catalog]
    if not ids or len(ids) != len(set(ids)): raise RuntimeError('EMPTY_OR_DUPLICATE_PUBLIC_CATALOG')
    r = {'kind':'PUBLIC_DOWNLOAD_NOT_SCORE','official_base':'https://three.arcprize.org',
         'python':platform.python_version(),'toolkit':importlib.metadata.version('arc-agi'),
         'catalog_ids':ids,'downloaded':[],'failed':[],'submission':False}
    dump(root/'acquisition.json',r)
    for item in catalog:
        try:
            env = arc.make(item.game_id, seed=0, save_recording=False)
            if env is None or type(env).__name__ != 'LocalEnvironmentWrapper': raise RuntimeError('LOCAL_WRAPPER_REQUIRED')
            folder = Path(env.info.local_dir).resolve()
            if not folder.is_relative_to(envdir.resolve()) or not (folder/'metadata.json').is_file(): raise RuntimeError('FILES_MISSING')
            r['downloaded'].append(item.game_id); print('DOWNLOADED',item.game_id,flush=True)
            del env
        except Exception as e: r['failed'].append({'game_id':item.game_id,'error_type':type(e).__name__})
        dump(root/'acquisition.json',r)
    families = {g.split('-')[0] for g in r['downloaded']}
    r['missing_known_public_families'] = sorted(EXPECTED-families)
    r['all_current_catalog_downloaded'] = len(r['downloaded']) == len(ids)
    r['inventory'] = [{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
                      for p in sorted(envdir.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    dump(root/'acquisition.json',r)
    print('ACQUISITION_SUMMARY',json.dumps({k:v for k,v in r.items() if k not in ('inventory','catalog_ids','downloaded')}),flush=True)
    if r['failed'] or not r['all_current_catalog_downloaded'] or r['missing_known_public_families']:
        raise RuntimeError('INCOMPLETE_PUBLIC_DOWNLOAD_SEE_RECEIPT')
def framehash(obs):
    frame = getattr(obs,'frame',None)
    if frame is None: raise RuntimeError('FRAME_MISSING')
    def convert(x):
        if hasattr(x,'tolist'): return x.tolist()
        raise TypeError(type(x).__name__)
    raw=json.dumps(frame,default=convert,separators=(',',':')).encode()
    if raw in (b'[]',b'null'): raise RuntimeError('EMPTY_FRAME')
    return hashlib.sha256(raw).hexdigest()
def smoke(root,seeds,steps):
    clean(); os.environ['OPERATION_MODE']='offline'
    attempts=[]
    def deny(event,args):
        if event in ('socket.connect','socket.getaddrinfo','socket.sendto','socket.bind'):
            attempts.append(event); raise RuntimeError('OFFLINE_NETWORK_DENIED')
    sys.addaudithook(deny)
    from arc_agi import Arcade, OperationMode
    from arcengine import GameState
    acquisition=json.loads((root/'acquisition.json').read_text(encoding='utf-8'))
    for item in acquisition['inventory']:
        p=root/item['path']
        if not p.is_file() or sha(p)!=item['sha256']: raise RuntimeError('ASSET_HASH_MISMATCH:'+item['path'])
    arc=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(root/'environment_files'),
               recordings_dir=str(root/'smoke_records'),logger=quiet())
    ids=sorted(e.game_id for e in arc.get_environments())
    if ids!=acquisition['catalog_ids']: raise RuntimeError('OFFLINE_CATALOG_MISMATCH')
    rows=[]
    for gid in ids:
        for seed in seeds:
            t=time.monotonic(); row={'game_id':gid,'seed':seed,'success':False,'action_count':0}
            try:
                env=arc.make(gid,seed=seed,save_recording=False)
                if env is None or type(env).__name__!='LocalEnvironmentWrapper': raise RuntimeError('NOT_LOCAL')
                obs=env.observation_space
                if obs is None: obs=env.reset()
                if obs is None: raise RuntimeError('RESET_FAILED')
                initial=framehash(obs); rng=random.Random(seed)
                for _ in range(steps):
                    if obs.state in (GameState.WIN,GameState.GAME_OVER): break
                    legal=sorted(env.action_space,key=lambda a:a.name)
                    if not legal: raise RuntimeError('NO_ACTIONS')
                    action=rng.choice(legal)
                    data={'x':rng.randrange(64),'y':rng.randrange(64)} if action.is_complex() else {}
                    obs=env.step(action,data=data)
                    if obs is None: raise RuntimeError('STEP_FAILED')
                    framehash(obs); row['action_count']+=1
                row.update(success=True,initial_frame_sha256=initial,final_frame_sha256=framehash(obs),
                           state=obs.state.name,levels_completed=int(obs.levels_completed))
                del env
            except Exception as e: row.update(error_type=type(e).__name__,error=str(e)[:180])
            row['seconds']=round(time.monotonic()-t,6); rows.append(row)
            print('OFFLINE_SMOKE',gid,seed,row['success'],row['action_count'],flush=True)
    r={'kind':'ENVIRONMENT_SMOKE_NOT_SOLVER_BENCHMARK','python':platform.python_version(),
       'platform':platform.platform(),'toolkit':importlib.metadata.version('arc-agi'),'game_count':len(ids),
       'seeds':seeds,'cases':len(rows),'passed':sum(x['success'] for x in rows),
       'network_mode':'OFFLINE','python_network_attempts':attempts,
       'os_network_namespace_expected':os.getenv('ARC_SMOKE_NETNS')=='1',
       'real_llm':False,'competition_submission':False,'official_score_claim':False,'rows':rows}
    dump(root/'offline_smoke.json',r)
    print('OFFLINE_SUMMARY',json.dumps({k:v for k,v in r.items() if k!='rows'}),flush=True)
    if r['passed']!=len(rows) or attempts: raise RuntimeError('OFFLINE_SMOKE_FAILED')
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('mode',choices=['acquire','smoke'])
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--seeds',default='0,1,2');p.add_argument('--steps',type=int,default=8)
    a=p.parse_args();root=a.root.resolve();root.mkdir(parents=True,exist_ok=True);os.chdir(root)
    if (root/'.env').exists() or (root/'.env.example').exists(): raise RuntimeError('DOTENV_NOT_ALLOWED_IN_PACK')
    if a.mode=='acquire': acquire(root)
    else:
        seeds=[int(s) for s in a.seeds.split(',')]
        if not seeds or not 1<=a.steps<=1000: raise ValueError('INVALID_SMOKE_BOUNDS')
        smoke(root,seeds,a.steps)
if __name__=='__main__': main()
