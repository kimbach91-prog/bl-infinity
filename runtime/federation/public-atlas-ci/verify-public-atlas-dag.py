"""CI qualification of bounded, receipt-bearing Dask atlas partitions."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time
from urllib.parse import urlsplit

def require(ok,reason):
    if not ok:raise ValueError(reason)
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def validate_input(inp):
    require(type(inp) is dict and inp.get('schema')=='deus-public-atlas-ci-input/1' and inp.get('data_class')=='PUBLIC','PUBLIC_INPUT')
    rows=inp.get('records');require(type(rows) is list and 1<=len(rows)<=128,'INPUT_BOUND')
    ids=[]
    for r in rows:
        require(set(r)=={'source_entity','label','repositories'},'RECORD_FIELDS')
        require(type(r['source_entity']) is str and r['source_entity'].startswith('http://www.wikidata.org/entity/Q'),'SOURCE_ID')
        require(type(r['label']) is str and 0<len(r['label'])<=512,'LABEL')
        require(type(r['repositories']) is list and 1<=len(r['repositories'])<=16,'REPOSITORY_BOUND')
        for u in r['repositories']:
            p=urlsplit(u)
            require(p.scheme in ('http','https') and p.hostname and p.username is None and p.password is None and len(u)<=4096,'PUBLIC_REPOSITORY_URI')
        ids.append(r['source_entity'])
    require(len(ids)==len(set(ids)),'DUPLICATE_SOURCE_ID')
    return rows
def oracle(rows):
    pairs=sorted(set((r['source_entity'],u) for r in rows for u in r['repositories']))
    hosts=dict(sorted(Counter(urlsplit(u).hostname.lower() for _,u in pairs).items()))
    return {'repository_pairs':[list(p) for p in pairs],'host_counts':hosts,'source_count':len(rows),'pair_digest':digest(pairs)}
def partition(index,rows):
    from distributed import get_worker
    worker=get_worker();started=utc()
    result=oracle(rows)
    return {'partition':index,'records':len(rows),'result':result,'worker_address':worker.address,'pid':os.getpid(),'started_at_utc':started,'completed_at_utc':utc(),'digest':digest(result)}
def reduce_partitions(parts,rows):
    require(type(parts) is list and len(parts)==4 and sorted(p['partition'] for p in parts)==list(range(4)),'ALL_PARTITIONS')
    for p in parts:require(p['digest']==digest(p['result']),'PARTITION_DIGEST')
    require(sum(p['records'] for p in parts)==len(rows),'RECORD_COVERAGE')
    expected=oracle(rows)
    pairs=sorted(set(tuple(v) for p in parts for v in p['result']['repository_pairs']))
    require(pairs==[tuple(v) for v in expected['repository_pairs']],'PAIR_ORACLE')
    merged_hosts=Counter()
    for p in parts:merged_hosts.update(p['result']['host_counts'])
    require(dict(sorted(merged_hosts.items()))==expected['host_counts'],'HOST_ORACLE')
    return expected
def worker_snapshot(dask_worker=None):
    import psutil
    return {'address':dask_worker.address,'pid':os.getpid(),'hostname':platform.node(),'cpu_count_observed':os.cpu_count(),'total_memory_bytes_observed':psutil.virtual_memory().total,'configured_threads':dask_worker.nthreads,'configured_memory_limit_bytes':dask_worker.memory_manager.memory_limit}
def execute(input_path,output):
    # This entry is admitted only within a GitHub-hosted CI job for this public repo.
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='kimbach91-prog/bl-infinity' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','GITHUB_HOSTED_CI_ONLY')
    from distributed import Client,LocalCluster
    raw=Path(input_path).read_bytes();require(len(raw)<=65536,'SOURCE_BYTES_BOUND')
    inp=json.loads(raw);rows=validate_input(inp);started=utc();clock=time.monotonic()
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    workers={};parts=[]
    with LocalCluster(n_workers=2,threads_per_worker=1,processes=True,host='127.0.0.1',dashboard_address=None,memory_limit='512MiB') as cluster:
        with Client(cluster,timeout='30s') as client:
            client.wait_for_workers(2,timeout=30)
            workers=client.run(worker_snapshot)
            addresses=sorted(workers)
            require(len(addresses)==2 and len({w['pid'] for w in workers.values()})==2,'TWO_PROCESS_WORKERS')
            futures=[client.submit(partition,i,rows[i::4],workers=[addresses[i%2]],allow_other_workers=False,pure=False,retries=0) for i in range(4)]
            parts=client.gather(futures)
            expected=reduce_partitions(parts,rows)
            require({p['worker_address'] for p in parts}==set(addresses),'BOTH_WORKERS_USED')
    # A successful context exit closes the local scheduler/workers on the ephemeral runner.
    finished=utc()
    files=[Path(__file__),Path(input_path)]
    source_pins=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    result={'schema':'deus-public-atlas-dask-ci-result/1','state':'PASS_BOUNDED_PUBLIC_ATLAS_DAG','task_id':inp['task_id'],'data_class':'PUBLIC','input_sha256':hashlib.sha256(raw).hexdigest(),'policy_binding':inp['policy_binding'],'source_pins':source_pins,'source_head_sha':os.environ.get('DEUS_SOURCE_HEAD_SHA'),'github_event_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),'github_job':os.environ.get('GITHUB_JOB'),'runner_environment':os.environ.get('RUNNER_ENVIRONMENT'),'runner_name':os.environ.get('RUNNER_NAME'),'runner_os':os.environ.get('RUNNER_OS'),'runner_arch':os.environ.get('RUNNER_ARCH'),'started_at_utc':started,'completed_at_utc':finished,'elapsed_ms':(time.monotonic()-clock)*1000,'dependency_versions':{n:importlib.metadata.version(n) for n in ['dask','distributed','cloudpickle','psutil']},'workers':workers,'partitions':parts,'verified_output':expected,'dask_scheduler_and_workers_closed':True,'new_accounts':0,'new_persistent_hosts':0,'current_physical_capacity_credit':0,'scope':'One bounded project CI qualification on one GitHub-hosted runner with two subprocess workers; no external worker network, persistent VPS, generic compute service, performance speedup or AGI admission.'}
    (out/'result.json').write_bytes(canonical(result))
    (out/'public-input.json').write_bytes(raw)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:result[k] for k in ['state','task_id','github_run_id','source_head_sha','elapsed_ms','dependency_versions','dask_scheduler_and_workers_closed']}))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();execute(a.input,a.output)
if __name__=='__main__':main()
