#!/usr/bin/env python3
"""Public Azure service-tag snapshot -> existing offline Internet atlas.
Two intended publisher reads per due refresh or explicit parser repair; no IP probe.
Source-local failure preserves the last good source and all other atlas tables.
"""
from __future__ import annotations
import argparse, hashlib, html, json, os, platform, re, resource
import shutil, sqlite3, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import internet_atlas_cloud_delta as core

VERSION = 'internet-atlas-azure/1.0.1'
SID = 'AZURE_PUBLIC_SERVICE_TAGS'
PAGE = 'https://www.microsoft.com/en-us/download/details.aspx?id=56519'
TTL = 86400
BOUNDARY = 'PUBLISHER_SERVICE_TAG_SNAPSHOT_ONLY; NO_IP_PROBING; NO_LIVENESS_OR_COMPUTE_AUTHORITY; NOT_ALL_INTERNET'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('REDIRECT_REQUIRES_REVIEW')

def read_public(url, headers=None):
    """Only the publisher index or its exact dated JSON payload is allowed."""
    p = urllib.parse.urlsplit(url)
    if url != PAGE and not valid_payload_url(url):
        raise ValueError('UNAPPROVED_PUBLIC_SOURCE_URL')
    if p.username or p.password or p.port not in (None, 443):
        raise ValueError('INVALID_PUBLIC_SOURCE_AUTHORITY')
    limit = (2 if url == PAGE else 16) * 1024 * 1024
    req = urllib.request.Request(url, headers={'User-Agent':'DEUS-Public-Atlas-Azure/1.0', 'Accept':'application/json,text/html', **(headers or {})})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as r:
            b = r.read(limit + 1)
            if len(b) > limit:
                raise ValueError('SOURCE_BODY_LIMIT')
            return r.status, dict(r.headers), b
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 304, dict(e.headers), b''
        raise

def valid_payload_url(url):
    p = urllib.parse.urlsplit(url)
    return bool(p.scheme == 'https' and p.hostname == 'download.microsoft.com' and not p.username and not p.password and p.port in (None,443) and not p.query and not p.fragment and re.fullmatch(r'/download/[A-Za-z0-9/_-]+/ServiceTags_Public_[0-9]{8}\.json', p.path))

def discover(body, now):
    text = html.unescape(body.decode('utf-8')).replace('\\/', '/')
    urls = set(re.findall(r'https://download\.microsoft\.com/download/[A-Za-z0-9/_-]+/ServiceTags_Public_[0-9]{8}\.json', text))
    dated = []
    today = datetime.fromtimestamp(now, timezone.utc).date()
    for u in urls:
        if not valid_payload_url(u):
            continue
        stamp = re.search(r'_([0-9]{8})\.json$', u)[1]
        d = datetime.strptime(stamp, '%Y%m%d').date()
        if d > today:
            raise ValueError('FUTURE_PUBLISHER_DATE')
        dated.append((d,u))
    if not dated:
        raise ValueError('NO_OFFICIAL_JSON_LINK')
    date,url = max(dated)
    return url, date.isoformat(), (today-date).days

def parse_payload(body):
    o = json.loads(body)
    if o.get('cloud') != 'Public' or not isinstance(o.get('changeNumber'), int) or isinstance(o.get('changeNumber'), bool):
        raise ValueError('AZURE_CLOUD_VERSION_SCHEMA')
    if not isinstance(o.get('values'), list) or not o['values']:
        raise ValueError('EMPTY_SERVICE_TAGS')
    result = {}; tags = set(); regions = set()
    for tag in o['values']:
        name = tag['name']; prop = tag['properties']; prefixes = prop['addressPrefixes']
        if not isinstance(name,str) or not name or not isinstance(prefixes,list):
            raise ValueError('AZURE_TAG_SCHEMA')
        tags.add(name)
        if prop.get('region'): regions.add(prop['region'])
        features = prop.get('networkFeatures')
        if features is None:
            features = []
        if not isinstance(features,list) or not all(isinstance(x,str) for x in features):
            raise ValueError('AZURE_FEATURE_LIST_SCHEMA')
        # Preserve each published tag/region combination, not Cartesian products.
        meta = {'service':prop.get('systemService',''), 'region':prop.get('region',''), 'category':name, 'cloud':'Public', 'tagId':tag.get('id'), 'tagChangeNumber':prop.get('changeNumber'), 'networkFeatures':sorted(features)}
        for prefix in prefixes:
            canonical,_,_,_,_ = core.projection(prefix)
            result[core.digest([canonical,meta])] = {'prefix':canonical,'meta':meta}
    rows = sorted(result.values(), key=lambda x:(x['prefix'],core.packed(x['meta'])))
    return rows, {'changeNumber':o['changeNumber'], 'tags':len(tags), 'regions':len(regions), 'uniquePrefixes':len({x['prefix'] for x in rows})}

def refresh(cache, now=None, fetcher=read_public, minimum=1000):
    now = time.time() if now is None else now
    cache=Path(cache); cache.mkdir(parents=True,exist_ok=True)
    p=cache/'azure.json'; hp=cache/'azure.hold.json'
    old=json.loads(p.read_text()) if p.exists() else None
    if old and (old.get('id')!=SID or old.get('url')!=PAGE or core.digest(old.get('rows'))!=old.get('semanticSha256') or not valid_payload_url(old.get('payloadUrl',''))):
        raise ValueError('AZURE_SOURCE_CACHE_TAMPER')
    rec={'id':SID,'networkRequests':0,'bodyBytes':0,'attempts':[],'state':'UNKNOWN'}
    if hp.exists():
        hold=json.loads(hp.read_text())
        # Run36017383609 returned HTTP200 for both publisher reads, then this
        # precise nullable-field parser failure. One new-parser attempt is safe;
        # HTTP/auth/429 failures never qualify for this exception.
        repaired=(hold.get('parserVersion')!=VERSION and hold.get('error')=="TypeError:'NoneType' object is not iterable")
        if now<hold.get('retryEpoch',0) and not repaired:
            rec['state']='HOLD_BACKOFF_LAST_GOOD' if old else 'HOLD_BACKOFF_NO_SNAPSHOT'
            return old,rec
        if repaired:
            rec['retryReason']='NULLABLE_FEATURE_PARSER_REPAIRED'
            rec['priorFailure']=hold
            core.atomic(cache/'azure.previous-parser-failure.json',hold)
    if old and now<old['nextCheckEpoch']:
        rec['state']='SKIP_NOT_DUE'; return old,rec
    def get(url,headers=None):
        a={'url':url}; rec['attempts'].append(a); rec['networkRequests']+=1
        status,h,b=fetcher(url,headers or {});rec['bodyBytes']+=len(b)
        a.update(status=status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        return status,{k.lower():v for k,v in h.items()},b
    try:
        status,_,page=get(PAGE)
        if status!=200: raise ValueError('PUBLISHER_INDEX_HTTP')
        url,date,age=discover(page,now)
        headers={}
        if old and old['payloadUrl']==url:
            if old.get('etag'): headers['If-None-Match']=old['etag']
            if old.get('lastModified'): headers['If-Modified-Since']=old['lastModified']
        status,h,body=get(url,headers)
        if status==304:
            if not old or old['payloadUrl']!=url: raise ValueError('304_WITHOUT_IDENTICAL_SOURCE')
            current={**old,'validatedAt':core.utc(),'nextCheckEpoch':now+TTL,'publisherDateAgeDays':age}
            rec['state']='UNCHANGED_304'
        elif status==200:
            # Preserve failure evidence before parsing; do not overwrite accepted
            # raw source bytes until the semantic integrity gate passes.
            (cache/'last-attempt.raw.json').write_bytes(body)
            rows,summary=parse_payload(body)
            if len(rows)<minimum: raise ValueError('SHORT_SOURCE')
            if old and (summary['changeNumber']<old['summary']['changeNumber'] or len(rows)<len(old['rows'])/2):
                raise ValueError('SOURCE_REGRESSION_REQUIRES_REVIEW')
            current={'id':SID,'url':PAGE,'payloadUrl':url,'publisherDate':date,'publisherDateAgeDays':age,'publicationFreshness':'RECENT_PUBLISHED_DATE' if age<=21 else 'STALE_PUBLISHED_DATE_NOT_CURRENT','observedAt':core.utc(),'validatedAt':core.utc(),'nextCheckEpoch':now+TTL,'rows':rows,'summary':summary,'bodySha256':hashlib.sha256(body).hexdigest(),'semanticSha256':core.digest(rows),'etag':h.get('etag'),'lastModified':h.get('last-modified')}
            core.atomic(cache/'publisher-payload.json',json.loads(body))
            (cache/'publisher-payload.raw.json').write_bytes(body)
            rec['state']='UNCHANGED_SEMANTICS' if old and old['semanticSha256']==current['semanticSha256'] else 'ACCEPTED_PUBLISHED_SNAPSHOT'
        else: raise ValueError('PAYLOAD_HTTP_STATUS')
        core.atomic(p,current)
        if hp.exists():hp.unlink()
        rec.update(rows=len(current['rows']),semanticSha256=current['semanticSha256'],payloadUrl=url,publisherDate=date,publisherDateAgeDays=age)
        return current,rec
    except Exception as e:
        rec.update(state='HOLD_LAST_GOOD' if old else 'HOLD_NO_SNAPSHOT',error=type(e).__name__+':'+str(e)[:200])
        core.atomic(hp,{'retryEpoch':now+TTL,'error':rec['error'],'dataFreshnessNotAdvanced':True,'parserVersion':VERSION})
        return old,rec

def execute(parent,expected,out,cache):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    t=time.perf_counter();c=time.process_time()
    source,r=refresh(cache);core.atomic(out/'source-attempt.json',r)
    if not source: raise ValueError('AZURE_SOURCE_HELD_NO_SNAPSHOT')
    rec=core.build_overlay(parent,expected,{SID:source},out/'snapshots')
    dbp=out/'snapshots'/rec['snapshot']/'overlay.sqlite'
    with sqlite3.connect('file:'+str(dbp)+'?mode=ro',uri=True) as db:
        actual=db.execute('SELECT COUNT(*) FROM cloud_prefixes WHERE source=?',(SID,)).fetchone()[0]
        if actual!=len(source['rows']): raise ValueError('AZURE_ROW_READBACK_MISMATCH')
        if core.noncloud_fingerprint(db)!=rec['noncloudFingerprint']: raise ValueError('NONCLOUD_READBACK_MISMATCH')
    if core.file_sha(dbp)!=rec['overlaySha256']: raise ValueError('DB_READBACK_HASH_MISMATCH')
    second,rr=refresh(cache)
    if rr['networkRequests'] or not second or second['semanticSha256']!=source['semanticSha256']: raise ValueError('IMMEDIATE_REUSE_FAILURE')
    warm=core.build_overlay(parent,expected,{SID:source},out/'snapshots')
    if not warm['invocation']['cacheHit']: raise ValueError('COMPILED_CACHE_MISS')
    bench=core.benchmark(dbp,queries=128,repeats=5)
    runtime={'python':platform.python_version(),'platform':platform.platform(),'cpuCountReported':os.cpu_count(),'cpuAffinityCount':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,'peakRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'cpuSeconds':time.process_time()-c,'elapsedSeconds':time.perf_counter()-t}
    for path in ['/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/memory.max']:
        if Path(path).exists():runtime[Path(path).name]=Path(path).read_text().strip()
    manifest={'schema':VERSION,'verdict':'PASS_SOURCE_LOCAL_AZURE_EXPANSION','generatedAt':core.utc(),'workflowRunId':os.getenv('GITHUB_RUN_ID'),'codeSha':os.getenv('GITHUB_SHA'),'source':{k:v for k,v in source.items() if k!='rows'},'sourceReceipt':r,'immediateReuse':rr,'overlay':rec,'warmReuse':warm['invocation'],'benchmark':bench,'runtime':runtime,'otherSourceHttpRequests':0,'executionAdmitted':False,'truthBoundary':BOUNDARY}
    core.atomic(out/'manifest.json',manifest)
    shutil.copy2(__file__,out/Path(__file__).name)
    print(json.dumps({'verdict':manifest['verdict'],'azureAssociations':actual,'azureUniquePrefixes':source['summary']['uniquePrefixes'],'allCloudAssociations':rec['cloudAssociations'],'allCloudUniquePrefixes':rec['uniqueCloudPrefixes'],'addedPrefixes':rec['addedUniquePrefixes'],'removedPrefixes':rec['removedUniquePrefixes'],'noncloudPreserved':rec['noncloudPreserved'],'httpRequests':r['networkRequests'],'bodyBytes':r['bodyBytes'],'sourceDate':source['publisherDate'],'dateAgeDays':source['publisherDateAgeDays'],'indexedQueriesPerSecond':bench['indexedMedianQueriesPerSecond'],'matchedRatio':bench['scanOverIndexedMedianRatio']}))
    return manifest

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--parent-db',type=Path,required=True);a.add_argument('--parent-sha256',required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--cache',type=Path,required=True);p=a.parse_args();execute(p.parent_db,p.parent_sha256,p.out,p.cache)
