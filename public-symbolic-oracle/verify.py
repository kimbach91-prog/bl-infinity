"""Portable PUBLIC regression-shard runner for the symbolic oracle project module."""
import argparse,hashlib,importlib.util,json,os,pathlib,platform,subprocess,time
from datetime import datetime,timezone
HERE=pathlib.Path(__file__).resolve().parent
def pack(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def need(x,c):
    if not x:raise ValueError(c)
def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--manifest',required=True);p.add_argument('--shard',type=int,required=True);p.add_argument('--shards',type=int,default=3);p.add_argument('--output',required=True);p.add_argument('--local',action='store_true');a=p.parse_args();need(a.shards==3 and 0<=a.shard<3,'THREE_BOUNDED_SHARDS')
    source=(HERE/'oracle.py').read_bytes();cases_path=pathlib.Path(a.cases);raw=cases_path.read_bytes();data=json.loads(raw);manifest_raw=pathlib.Path(a.manifest).read_bytes();manifest=json.loads(manifest_raw);need(data['data_class']=='PUBLIC' and data['schema']=='deus-public-symbolic-regression-cases/1' and len(data['cases'])==8,'PUBLIC_CASES_ONLY');need(sha(source)==manifest['oracle_sha256'] and sha(raw)==manifest['cases_sha256'] and sha(pathlib.Path(__file__).read_bytes())==manifest['harness_sha256'],'EXACT_PUBLISHED_SOURCE_INPUT')
    allowed={'public-symbolic-oracle/oracle.py','public-symbolic-oracle/verify.py','public-symbolic-oracle/public-cases.json','public-symbolic-oracle/README.md','.github/workflows/deus-public-symbolic-oracle-ci.yml'};need(set(manifest['published_files'])==allowed,'CLOSED_PUBLIC_SOURCE_MANIFEST')
    for path,pin in manifest['published_files'].items():
        b=(HERE.parent/path).read_bytes();need(len(b)==pin['bytes'] and sha(b)==pin['sha256'],'ALL_PUBLISHED_SOURCE_BYTES')
    spec=importlib.util.spec_from_file_location('deus_public_symbolic_oracle',HERE/'oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    observed=[];start=time.monotonic()
    for i,c in enumerate(data['cases']):
        if i%3!=a.shard:continue
        acceptance=oracle.verify(c['variables'],c['name'],c['arguments'],c['result']);observed.append({'index':i,'case_id':c['id'],'case_sha256':sha(pack(c)),'original_provider_receipt_sha256':c['provider_receipt_sha256'],'acceptance':acceptance})
    need(len(observed)==[3,3,2][a.shard],'EXACT_SHARD_COVERAGE')
    negative=[]
    for label,fn in [('nonpolynomial_ast',lambda:oracle.prepare(['x'],'expand_expression',{'expr':'x.__class__'})),('wrong_derivative',lambda:oracle.verify(['x'],'differentiate',{'expr':'x**3','variable':'x'},'3*x**2+1')),('inconsistent_system',lambda:oracle.prepare(['v0'],'solve_linear_system',{'system':['v0-1','v0-2'],'variables':['v0']}))]:
        try:fn()
        except ValueError as e:negative.append({'case':label,'guard':str(e)})
    need(len(negative)==3,'REJECTS_INVALID_INPUT_AND_RESULT')
    if a.local:head='LOCAL_CONTROLLED_SELF_TEST';mode='LOCAL_SELF_TEST_NOT_PROVIDER_EXECUTION'
    else:
        need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('GITHUB_REPOSITORY')==manifest['repository'],'HOSTED_PROJECT_CI_ONLY');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip();need(head==os.environ.get('DEUS_CI_EXPECTED_HEAD'),'CHECKED_OUT_SOURCE_HEAD');mode='ATTRIBUTABLE_GITHUB_HOSTED_PROJECT_CI'
    env_keys=['GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_REPOSITORY','GITHUB_JOB','RUNNER_NAME','RUNNER_OS','RUNNER_ARCH','RUNNER_ENVIRONMENT']
    result={'schema':'deus-public-symbolic-ci-shard/1','state':'PASS_PUBLIC_SYMBOLIC_REGRESSION_SHARD','task_id':data['task_id'],'data_class':'PUBLIC','mode':mode,'source_head_sha':head,'source_sha256':{'oracle.py':sha(source),'verify.py':sha(pathlib.Path(__file__).read_bytes()),'public-cases.json':sha(raw),'source-manifest.json':sha(manifest_raw)},'policy_binding':data['policy_binding'],'shard':a.shard,'shards':3,'observed':observed,'negative_controls':negative,'elapsed_ms':round((time.monotonic()-start)*1000,3),'provider_environment':{k:os.environ.get(k) for k in env_keys} if not a.local else {},'runtime_metadata':{'python':platform.python_version(),'platform':platform.system(),'machine':platform.machine(),'logical_cpu_count':os.cpu_count()},'scope':'One bounded project CI shard over public source/cases;metadata is not a continuing capacity lease or speedup claim','physical_capacity_credit_after_job':0,'external_result_service_requests':0,'background_started':False,'finished_at_utc':datetime.now(timezone.utc).isoformat()}
    out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    artifacts={'result.json':pack(result),'oracle.py':source,'verify.py':pathlib.Path(__file__).read_bytes(),'public-cases.json':raw,'source-manifest.json':manifest_raw,'workflow.yml':(HERE.parent/'.github/workflows/deus-public-symbolic-oracle-ci.yml').read_bytes(),'README.md':(HERE/'README.md').read_bytes()}
    for name,b in artifacts.items():
        with (out.parent/name).open('xb')as f:f.write(b)
    print(json.dumps({'state':result['state'],'shard':a.shard,'verified_cases':len(observed),'negative_controls':len(negative),'mode':mode,'output_sha256':sha(pack(result))}))
if __name__=='__main__':main()
