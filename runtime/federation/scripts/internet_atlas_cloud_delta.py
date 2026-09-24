#!/usr/bin/env python3
"""Isolated public cloud-range deltas and matched offline lookup measurements.
No address probing or execution/lease admission. Failed families retain last good
rows. Parent overlay and non-cloud tables are immutable. Python standard library.
"""
from __future__ import annotations
import argparse, hashlib, ipaddress, json, os, platform, random, resource
import shutil, sqlite3, statistics, tempfile, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
VERSION='internet-atlas-cloud-delta/1.0.0'
BOUNDARY='PUBLISHED_SERVICE_RANGE_ONLY; NO_HOST_PROBE; NO_LIVENESS_OR_OWNERSHIP_INFERENCE; NO_COMPUTE_ADMISSION; NOT_ALL_INTERNET'
SOURCES=[
 ('AWS_IP_RANGES','https://ip-ranges.amazonaws.com/ip-ranges.json','aws',1000,21600),
 ('GCP_CLOUD_RANGES','https://www.gstatic.com/ipranges/cloud.json','google',100,21600),
 ('GOOGLE_GLOBAL_RANGES','https://www.gstatic.com/ipranges/goog.json','google',100,21600),
 ('CLOUDFLARE_IPV4','https://www.cloudflare.com/ips-v4','lines',1,21600),
 ('CLOUDFLARE_IPV6','https://www.cloudflare.com/ips-v6','lines',1,21600),
 ('GITHUB_META','https://api.github.com/meta','github',100,21600),
 ('FASTLY_PUBLIC_IPS','https://api.fastly.com/public-ip-list','fastly',1,21600),
 ('OCI_PUBLIC_RANGES','https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json','oracle',100,86400),
 ('ATLASSIAN_PUBLIC_RANGES','https://ip-ranges.atlassian.com/','atlassian',10,86400),
]
def utc():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def packed(o):return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(o):return hashlib.sha256(packed(o)).hexdigest()
def sql_scalar(v):return packed(v).decode() if isinstance(v,(list,dict)) else v
def file_sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def atomic(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    with t.open('wb') as f:f.write(packed(o)+b'\n');f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def projection(prefix):
    n=ipaddress.ip_network(prefix,strict=True)
    if n.prefixlen==0:raise ValueError('DEFAULT_RANGE_REQUIRES_REVIEW')
    k=hashlib.sha256(('cidr|'+str(n)).encode()).hexdigest()
    return str(n),n.prefixlen,n.version,k,str(int(k,16)%10**12)
def parse(kind,body):
    """Deduplicate full (prefix, metadata), never prefix alone or Cartesian tags."""
    obj=None if kind=='lines' else json.loads(body);raw=[]
    if kind=='aws':
        for r in obj['prefixes']+obj.get('ipv6_prefixes',[]):raw.append((r.get('ip_prefix') or r.get('ipv6_prefix'),{k:v for k,v in r.items() if k not in ('ip_prefix','ipv6_prefix')}))
    elif kind=='google':
        for r in obj['prefixes']:raw.append((r.get('ipv4Prefix') or r.get('ipv6Prefix'),{k:v for k,v in r.items() if k not in ('ipv4Prefix','ipv6Prefix')}))
    elif kind=='lines':raw=[(p.strip(),{}) for p in body.decode().splitlines() if p.strip()]
    elif kind=='github':
        for k,v in obj.items():
            if isinstance(v,list):
                for p in v:
                    if isinstance(p,str) and '/' in p and not p.startswith(('http:','https:')):raw.append((p,{'category':k}))
    elif kind=='fastly':raw=[(p,{}) for p in obj['addresses']+obj.get('ipv6_addresses',[])]
    elif kind=='oracle':
        for region in obj['regions']:
            for r in region['cidrs']:raw.append((r['cidr'],{'region':region['region'],'tags':sorted(r.get('tags',[]))}))
    elif kind=='atlassian':
        for r in obj['items']:raw.append((r['cidr'],{k:(sorted(v) if isinstance(v,list) else v) for k,v in r.items() if k not in ('cidr','network','mask')}))
    else:raise ValueError('UNSUPPORTED_PARSER')
    result={}
    for prefix,meta in raw:
        prefix,_,_,_,_=projection(prefix);result[digest([prefix,meta])]={'prefix':prefix,'meta':meta}
    return sorted(result.values(),key=lambda r:(r['prefix'],packed(r['meta'])))
class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        from urllib.parse import urlsplit
        old,new=urlsplit(req.full_url),urlsplit(newurl)
        if new.scheme!='https' or old.hostname!=new.hostname:raise ValueError('CROSS_ORIGIN_REDIRECT_HELD')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def http_read(url,headers):
    req=urllib.request.Request(url,headers={'User-Agent':'DEUS-Public-Atlas-CloudDelta/1.0','Accept':'application/json,text/plain,*/*',**headers})
    opener=urllib.request.build_opener(SameOriginRedirect())
    try:
        with opener.open(req,timeout=25) as r:
            body=r.read(8*1024*1024+1)
            if len(body)>8*1024*1024:raise ValueError('BODY_SIZE_LIMIT')
            return r.status,dict(r.headers),body
    except urllib.error.HTTPError as e:
        if e.code==304:return 304,dict(e.headers),b''
        raise
def refresh(spec,cache,now=None,fetcher=http_read):
    sid,url,kind,minimum,ttl=spec;now=time.time() if now is None else now
    path=Path(cache)/(sid+'.json');hp=Path(cache)/(sid+'.hold.json')
    old=json.loads(path.read_text()) if path.exists() else None
    if old and (digest(old.get('rows'))!=old.get('semanticSha256') or old.get('id')!=sid or old.get('url')!=url):raise ValueError('CACHED_SOURCE_TAMPER:'+sid)
    t=time.perf_counter();rec={'id':sid,'url':url,'state':'UNKNOWN','networkRequests':0,'bodyBytes':0}
    if hp.exists():
        hold=json.loads(hp.read_text())
        if now<float(hold.get('retryEpoch',0)):
            rec.update(state='HELD_BACKOFF_LAST_GOOD' if old else 'HELD_BACKOFF_NO_SNAPSHOT',error=hold.get('error'),rows=len(old['rows']) if old else 0)
            return old,rec
    if old and now<float(old.get('nextCheckEpoch',0)):
        rec.update(state='SKIP_NOT_DUE',rows=len(old['rows']),bodySha256=old['bodySha256'],sourceObservedAt=old['observedAt']);return old,rec
    headers={}
    if old and old.get('etag'):headers['If-None-Match']=old['etag']
    if old and old.get('lastModified'):headers['If-Modified-Since']=old['lastModified']
    try:
        rec['networkRequests']=1;status,h,b=fetcher(url,headers);rec.update(status=status,bodyBytes=len(b));h={k.lower():v for k,v in h.items()}
        if status==304:
            if not old:raise ValueError('304_WITHOUT_LAST_GOOD')
            current={**old,'nextCheckEpoch':now+ttl,'validatedAt':utc()};rec['state']='UNCHANGED_304'
        elif status==200:
            rows=parse(kind,b)
            if len(rows)<minimum:raise ValueError('EMPTY_OR_SHORT_SOURCE:'+str(len(rows)))
            if old and len(rows)<0.5*len(old['rows']):raise ValueError('MAJOR_DROP_REQUIRES_REVIEW')
            sem=digest(rows)
            current={'id':sid,'url':url,'observedAt':utc(),'validatedAt':utc(),'rows':rows,'bodySha256':hashlib.sha256(b).hexdigest(),'semanticSha256':sem,'etag':h.get('etag'),'lastModified':h.get('last-modified'),'nextCheckEpoch':now+ttl}
            rec['state']='UNCHANGED_SEMANTICS' if old and old['semanticSha256']==sem else 'ACCEPTED_NEW_SNAPSHOT'
        else:raise ValueError('UNEXPECTED_HTTP_STATUS:'+str(status))
        atomic(path,current)
        if hp.exists():hp.unlink()
        rec.update(rows=len(current['rows']),bodySha256=current['bodySha256'],semanticSha256=current['semanticSha256'],sourceObservedAt=current['observedAt'])
    except Exception as e:
        current=old;error=type(e).__name__+':'+str(e)[:250]
        rec.update(state='HELD_LAST_GOOD' if old else 'HELD_NO_SNAPSHOT',error=error,rows=len(old['rows']) if old else 0)
        atomic(hp,{'id':sid,'url':url,'retryEpoch':now+ttl,'error':error,'dataFreshnessNotAdvanced':True})
    rec['elapsedSeconds']=round(time.perf_counter()-t,6);return current,rec
def collect(cache):
    Path(cache).mkdir(parents=True,exist_ok=True);accepted={};receipts=[]
    for spec in SOURCES:
        current,r=refresh(spec,cache);receipts.append(r)
        if current:accepted[spec[0]]=current
    return accepted,receipts
def noncloud_fingerprint(db):
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") if not r[0].startswith('cloud_')];out={}
    for table in sorted(tables):
        if not table.replace('_','').isalnum():raise ValueError('INVALID_TABLE_NAME')
        h=hashlib.sha256();count=0
        for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):h.update(packed(list(r)));count+=1
        out[table]={'rows':count,'sha256':h.hexdigest()}
    return out
def build_overlay(parent_db,expected_parent_sha,accepted,out):
    t=time.perf_counter();parent_db=Path(parent_db);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if file_sha(parent_db)!=expected_parent_sha:raise ValueError('PARENT_OVERLAY_TAMPER')
    semantic={k:v['semanticSha256'] for k,v in sorted(accepted.items())}
    key=digest([VERSION,expected_parent_sha,semantic]);dest=out/key;dest.mkdir(exist_ok=True);dbp=dest/'overlay.sqlite';rp=dest/'receipt.json'
    if rp.exists():
        rec=json.loads(rp.read_text())
        if rec['inputSemanticSha256']!=semantic or file_sha(dbp)!=rec['overlaySha256']:raise ValueError('DERIVED_CACHE_TAMPER')
        atomic(out/'CLOUD_CURRENT.json',{'snapshot':key,'receipt':str(Path(key)/'receipt.json')})
        return {**rec,'invocation':{'cacheHit':True,'elapsedSeconds':time.perf_counter()-t,'newRows':0,'networkRequests':0}}
    tmp=dest/'building.sqlite'
    if tmp.exists():tmp.unlink()
    with sqlite3.connect(f'file:{parent_db}?mode=ro',uri=True) as src,sqlite3.connect(tmp) as db:
        src.backup(db);before=noncloud_fingerprint(src)
        previous_unique={r[0] for r in src.execute('SELECT DISTINCT prefix FROM cloud_prefixes')};old_counts=dict(src.execute('SELECT source,COUNT(*) FROM cloud_prefixes GROUP BY source'))
        for sid,current in sorted(accepted.items()):
            db.execute('DELETE FROM cloud_prefixes WHERE source=?',(sid,));rows=[]
            for r in current['rows']:
                prefix,plen,family,k,slot=projection(r['prefix']);m=r['meta']
                rows.append((sid,prefix,plen,family,k,slot,*[sql_scalar(m.get(x)) for x in ('service','region','scope','category')],packed(m).decode()))
            db.executemany('INSERT INTO cloud_prefixes(source,prefix,plen,family,resource_key,slot_id,service,region,scope,category,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)',rows)
        db.execute('CREATE TABLE IF NOT EXISTS cloud_source_receipts(source TEXT PRIMARY KEY,body_sha256 TEXT,semantic_sha256 TEXT,observed_at TEXT,source_url TEXT)')
        db.executemany('INSERT OR REPLACE INTO cloud_source_receipts VALUES (?,?,?,?,?)',[(k,v['bodySha256'],v['semanticSha256'],v['observedAt'],v['url']) for k,v in sorted(accepted.items())])
        db.commit();after=noncloud_fingerprint(db)
        if before!=after:raise ValueError('NONCLOUD_CHANGED')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLITE_INTEGRITY')
        counts=dict(db.execute('SELECT source,COUNT(*) FROM cloud_prefixes GROUP BY source'));unique={r[0] for r in db.execute('SELECT DISTINCT prefix FROM cloud_prefixes')};semh=hashlib.sha256()
        for r in db.execute('SELECT source,prefix,metadata_json FROM cloud_prefixes ORDER BY source,prefix,metadata_json'):semh.update(packed(list(r)))
    os.replace(tmp,dbp)
    rec={'schema':VERSION,'snapshot':key,'generatedAt':utc(),'parentOverlaySha256':expected_parent_sha,'inputSemanticSha256':semantic,'overlaySha256':file_sha(dbp),'cloudAssociations':sum(counts.values()),'uniqueCloudPrefixes':len(unique),'previousUniquePrefixes':len(previous_unique),'addedUniquePrefixes':len(unique-previous_unique),'removedUniquePrefixes':len(previous_unique-unique),'previousFamilyRows':old_counts,'familyRows':counts,'cloudSemanticSha256':semh.hexdigest(),'noncloudFingerprint':after,'noncloudPreserved':True,'overlayBytes':dbp.stat().st_size,'integrity':'ok','networkRequestsDuringBuild':0,'executionAdmitted':False,'truthBoundary':BOUNDARY}
    rec['invocation']={'cacheHit':False,'elapsedSeconds':time.perf_counter()-t,'newRows':sum(len(v['rows']) for v in accepted.values()),'networkRequests':0}
    atomic(rp,rec);atomic(out/'CLOUD_CURRENT.json',{'snapshot':key,'receipt':str(Path(key)/'receipt.json')});return rec
def lookup(db,ip,indexed=True):
    a=ipaddress.ip_address(ip);keys=[str(ipaddress.ip_network((a,p),strict=False)) for p in range(a.max_prefixlen,-1,-1)]
    hint='INDEXED BY cloud_prefixes_prefix' if indexed else 'NOT INDEXED'
    return list(db.execute('SELECT source,prefix,service,region,scope,category,metadata_json FROM cloud_prefixes '+hint+' WHERE prefix IN ('+','.join('?'*len(keys))+') ORDER BY source,prefix,metadata_json',keys))
def benchmark(dbp,queries=128,repeats=5):
    """Same connection/SQL/results/host. Baseline is SQLite scan, not frontier AI.
    Includes ancestor generation, SQL, fetch and result-digest verification.
    """
    if not 8<=queries<=512 or not 3<=repeats<=9:raise ValueError('BOUNDED_BENCHMARK_ONLY')
    rng=random.Random(20260924)
    with sqlite3.connect(f'file:{dbp}?mode=ro',uri=True) as db:
        prefixes=[r[0] for r in db.execute('SELECT DISTINCT prefix FROM cloud_prefixes ORDER BY prefix')];rng.shuffle(prefixes)
        ips=[str(ipaddress.ip_network(p).network_address) for p in prefixes[:queries-4]]+['203.0.113.1','198.51.100.1','2001:db8::1','255.255.255.255']
        qhash=digest(ips);reference=None;timings={'indexed':[],'scan':[]};cpu={'indexed':[],'scan':[]}
        for mode in (True,False):lookup(db,ips[0],mode)
        for repeat in range(repeats):
            for mode in ([True,False] if repeat%2==0 else [False,True]):
                name='indexed' if mode else 'scan';h=hashlib.sha256();c=time.process_time();t=time.perf_counter()
                for ip in ips:h.update(packed([ip,lookup(db,ip,mode)]))
                elapsed=time.perf_counter()-t;cpu[name].append(time.process_time()-c);timings[name].append(elapsed);result=h.hexdigest()
                if reference is None:reference=result
                if reference!=result:raise ValueError('MATCHED_OUTPUT_MISMATCH')
    med={k:statistics.median(v) for k,v in timings.items()}
    return {'schema':'deus-matched-cloud-lookup-benchmark/1','queriesPerTrial':len(ips),'repeatsPerMode':repeats,'querySha256':qhash,'resultSha256':reference,'allOutputsIdentical':True,'seconds':timings,'cpuSeconds':cpu,'medianSeconds':med,'indexedMedianQueriesPerSecond':len(ips)/med['indexed'],'scanOverIndexedMedianRatio':med['scan']/med['indexed'],'networkRequests':0,'baseline':'same SQLite cloud table with NOT INDEXED; optimized uses existing prefix index','order':'alternating AB/BA, one connection, warmed first query','limitations':'bounded deterministic workload; includes process/page cache effects; not FLOPS, GPU equivalence, guaranteed capacity, service SLA or whole-DEUS speedup'}
def execute(parent_db,parent_sha,out,cache):
    started=time.perf_counter();cpu=time.process_time();accepted,receipts=collect(cache)
    if len(accepted)<7:raise ValueError('INSUFFICIENT_ACCEPTED_CLOUD_FAMILIES:'+str(len(accepted)))
    rec=build_overlay(parent_db,parent_sha,accepted,Path(out)/'snapshots');dbp=Path(out)/'snapshots'/rec['snapshot']/'overlay.sqlite'
    cold_times=[];warm_times=[]
    for i in range(3):
        with tempfile.TemporaryDirectory() as d:
            a=build_overlay(parent_db,parent_sha,accepted,Path(d));b=build_overlay(parent_db,parent_sha,accepted,Path(d))
            if a['cloudSemanticSha256']!=b['cloudSemanticSha256']:raise ValueError('CACHE_SEMANTIC_MISMATCH')
            cold_times.append(a['invocation']['elapsedSeconds']);warm_times.append(b['invocation']['elapsedSeconds'])
    accepted2,second=collect(cache)
    if any(r['networkRequests'] for r in second):raise ValueError('IMMEDIATE_REUSE_MUST_NOT_FETCH')
    if {k:v['semanticSha256'] for k,v in accepted.items()}!={k:v['semanticSha256'] for k,v in accepted2.items()}:raise ValueError('SOURCE_CACHE_DRIFT')
    b=benchmark(dbp);runtime={'python':platform.python_version(),'platform':platform.platform(),'cpuCountReported':os.cpu_count(),'cpuAffinityCount':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,'peakRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'cpuSeconds':time.process_time()-cpu,'elapsedSeconds':time.perf_counter()-started}
    for p in ['/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/memory.max']:
        if Path(p).exists():runtime[Path(p).name]=Path(p).read_text().strip()
    manifest={'schema':VERSION,'generatedAt':utc(),'verdict':'PASS_ISOLATED_CLOUD_DELTA_MATCHED_BENCH','codeSha':os.getenv('GITHUB_SHA'),'workflowRunId':os.getenv('GITHUB_RUN_ID'),'sourceReceipts':receipts,'immediateReuse':second,'overlay':rec,'benchmark':b,'buildReuseBenchmark':{'repeats':3,'coldSeconds':cold_times,'warmVerifiedSeconds':warm_times,'medianRatio':statistics.median(cold_times)/statistics.median(warm_times),'sameHostInputsAndSemantics':True,'networkRequests':0},'runtime':runtime,'publicSourceHttpRequests':sum(r['networkRequests'] for r in receipts),'publicSourceBodyBytes':sum(r['bodyBytes'] for r in receipts),'executionAdmitted':False,'truthBoundary':BOUNDARY}
    atomic(Path(out)/'manifest.json',manifest);shutil.copy2(__file__,Path(out)/Path(__file__).name)
    print(json.dumps({'verdict':manifest['verdict'],'sources':len(accepted),'cloudAssociations':rec['cloudAssociations'],'uniquePrefixes':rec['uniqueCloudPrefixes'],'addedPrefixes':rec['addedUniquePrefixes'],'noncloudPreserved':True,'lookupRatio':b['scanOverIndexedMedianRatio'],'indexedQueriesPerSecond':b['indexedMedianQueriesPerSecond'],'reuseRatio':manifest['buildReuseBenchmark']['medianRatio'],'httpRequests':manifest['publicSourceHttpRequests'],'bodyBytes':manifest['publicSourceBodyBytes']}));return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parent-db',required=True,type=Path);p.add_argument('--parent-sha256',required=True);p.add_argument('--out',required=True,type=Path);p.add_argument('--cache',required=True,type=Path);a=p.parse_args();execute(a.parent_db,a.parent_sha256,a.out,a.cache)
