#!/usr/bin/env python3
"""Offline, resumable public census/RIS index. No network access or authority inference."""
from __future__ import annotations
import argparse, hashlib, ipaddress, json, os, re, sqlite3, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
try:
    import orjson
    decode = orjson.loads
except ImportError:
    decode = json.loads
VERSION='internet-atlas-index/1.0.0'
BOUNDARY='SOURCE_SNAPSHOT_ONLY; NO_HOST_LIVENESS; NO_EXECUTION_AUTHORITY; NO_GLOBAL_COMPLETENESS'
SCHEMA='''
CREATE TABLE IF NOT EXISTS checkpoints(stage TEXT PRIMARY KEY,n INTEGER NOT NULL,done INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS allocations(id INTEGER PRIMARY KEY,prefix TEXT NOT NULL,plen INTEGER,family INTEGER,registry TEXT,country TEXT,status TEXT,source_date TEXT,descriptor_digest TEXT);
CREATE TABLE IF NOT EXISTS asn_ranges(id INTEGER PRIMARY KEY,first_asn INTEGER,last_asn INTEGER,registry TEXT,country TEXT,status TEXT,source_date TEXT);
CREATE TABLE IF NOT EXISTS peering(id INTEGER PRIMARY KEY,entity_type TEXT,source_id INTEGER,name TEXT,asn INTEGER,status TEXT,country TEXT,resource_key TEXT);
CREATE TABLE IF NOT EXISTS probes(id INTEGER PRIMARY KEY,probe_id TEXT,family INTEGER,asn INTEGER,source_status TEXT,declared_prefix TEXT,resource_key TEXT);
CREATE TABLE IF NOT EXISTS routes_v4(id INTEGER PRIMARY KEY,prefix TEXT NOT NULL,plen INTEGER,asn INTEGER,origin_raw TEXT,ris_peers INTEGER,relation_key TEXT);
CREATE TABLE IF NOT EXISTS routes_v6(id INTEGER PRIMARY KEY,prefix TEXT NOT NULL,plen INTEGER,asn INTEGER,origin_raw TEXT,ris_peers INTEGER,relation_key TEXT);
'''
INDEXES='''
CREATE INDEX IF NOT EXISTS allocations_prefix ON allocations(prefix);
CREATE INDEX IF NOT EXISTS asn_ranges_first ON asn_ranges(first_asn,last_asn);
CREATE INDEX IF NOT EXISTS peering_asn ON peering(asn);
CREATE INDEX IF NOT EXISTS probes_asn ON probes(asn);
CREATE INDEX IF NOT EXISTS probes_id ON probes(probe_id);
CREATE INDEX IF NOT EXISTS routes_v4_prefix ON routes_v4(prefix);
CREATE INDEX IF NOT EXISTS routes_v6_prefix ON routes_v6(prefix);
CREATE INDEX IF NOT EXISTS routes_v4_asn ON routes_v4(asn);
CREATE INDEX IF NOT EXISTS routes_v6_asn ON routes_v6(asn);
'''
def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def atomic_json(p:Path,obj:dict)->None:
    tmp=p.with_suffix(p.suffix+'.tmp')
    with tmp.open('w',encoding='utf8') as f:
        json.dump(obj,f,indent=2,sort_keys=True,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def verify_zip(p:Path,expected:str)->zipfile.ZipFile:
    if not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('EXPECTED_SHA256_REQUIRED')
    if sha256_file(p)!=expected:raise ValueError('ARTIFACT_SHA_MISMATCH')
    z=zipfile.ZipFile(p)
    if len(z.namelist())!=len(set(z.namelist())):raise ValueError('DUPLICATE_ZIP_MEMBER')
    if sum(f.file_size for f in z.infolist())>2*1024**3:raise ValueError('EXPANDED_SIZE_LIMIT')
    return z
def prefix_fields(text:str)->tuple:
    n=ipaddress.ip_network(text,strict=True)
    return str(n),n.prefixlen,n.version
def allocation(r:dict,n:int)->tuple:
    p,l,v=prefix_fields(r['cidr'])
    return n,p,l,v,r.get('registry'),r.get('cc'),r.get('status'),r.get('date'),r.get('descriptorDigest')
def asn_range(r:dict,n:int)->tuple:
    a,c=int(r['start']),int(r['value'])
    if a<0 or c<1 or a+c>2**32:raise ValueError('BAD_ASN_RANGE')
    return n,a,a+c-1,r.get('registry'),r.get('cc'),r.get('status'),r.get('date')
def peering(r:dict,n:int)->tuple:
    return n,r.get('entityType'),r.get('id'),r.get('name'),r.get('asn'),r.get('status'),r.get('country'),r.get('resourceKey')
def probe(r:dict,n:int)->tuple:
    v={'ipv4':4,'ipv6':6}.get(r.get('identityType'));s='V4' if v==4 else 'V6' if v==6 else None
    # Exact probe addresses and geolocation are deliberately omitted.
    return n,str(r['sourceId']),v,r.get('asn'+s) if s else None,r.get('status'),r.get('prefix'+s) if s else None,r.get('resourceKey')
def route(r:dict,n:int)->tuple:
    p,l,v=prefix_fields(r['prefix']);raw=str(r.get('origin',''));m=re.fullmatch(r'AS([0-9]+)',raw);a=int(m.group(1)) if m else None
    if a is not None and not 0<=a<2**32:raise ValueError('BAD_ORIGIN_ASN')
    return n,p,l,a,raw,r.get('numRisPeers'),r.get('relationKey')
STAGES=(('allocations','rir-address-descriptors.jsonl',allocation,9,'census'),('asn_ranges','rir-asn-records.jsonl',asn_range,7,'census'),('peering','peeringdb-topology.jsonl',peering,8,'census'),('probes','ripe-atlas-observed-devices.jsonl',probe,7,'census'),('routes_v4','ris-v4.jsonl',route,7,'routing'),('routes_v6','ris-v6.jsonl',route,7,'routing'))
def import_stage(db:sqlite3.Connection,z:zipfile.ZipFile,stage:tuple,batch_size:int=10000,stop_after:int|None=None)->dict:
    table,member,transform,width,_=stage
    old=db.execute('SELECT n,done FROM checkpoints WHERE stage=?',(table,)).fetchone();cursor,done=old if old else (0,0)
    if done:return dict(stage=table,rows=cursor,reused=True)
    sql=f"INSERT INTO {table} VALUES ({','.join('?' for _ in range(width))})";batch=[];n=0
    def commit(last:int,completed:bool=False)->None:
        with db:
            if batch:db.executemany(sql,batch)
            db.execute('INSERT INTO checkpoints VALUES (?,?,?) ON CONFLICT(stage) DO UPDATE SET n=excluded.n,done=excluded.done',(table,last,int(completed)))
        batch.clear()
    with z.open(member) as f:
        while True:
            line=f.readline(65537)
            if not line:break
            if len(line)>65536:raise ValueError('ROW_TOO_LARGE')
            if not line.strip():continue
            n+=1
            if n<=cursor:continue
            r=decode(line)
            if r.get('executionReady') is True:raise ValueError('UNEXPECTED_EXECUTION_CREDIT')
            batch.append(transform(r,n))
            if len(batch)>=batch_size:commit(n)
            if stop_after is not None and n>=stop_after:commit(n);return dict(stage=table,rows=n,interrupted=True)
    if n<cursor:raise ValueError('INPUT_SHORTER_THAN_CHECKPOINT')
    commit(n,True);return dict(stage=table,rows=n,resumedFrom=cursor,reused=False)
def scalar(db:sqlite3.Connection,sql:str,args:tuple=())->int:return int(db.execute(sql,args).fetchone()[0])
def report(db:sqlite3.Connection)->dict:
    counts={s[0]:scalar(db,f'SELECT COUNT(*) FROM {s[0]}') for s in STAGES}
    db.executescript('''CREATE TABLE IF NOT EXISTS origin_summary AS SELECT asn,SUM(v4) ipv4_observations,SUM(v6) ipv6_observations FROM (SELECT asn,COUNT(*) v4,0 v6 FROM routes_v4 WHERE asn IS NOT NULL GROUP BY asn UNION ALL SELECT asn,0,COUNT(*) FROM routes_v6 WHERE asn IS NOT NULL GROUP BY asn) GROUP BY asn; CREATE UNIQUE INDEX IF NOT EXISTS origin_summary_asn ON origin_summary(asn);''')
    return {'inputRows':counts,'unique':{'allocationPrefixes':scalar(db,'SELECT COUNT(DISTINCT prefix) FROM allocations'),'routingPrefixesV4':scalar(db,'SELECT COUNT(DISTINCT prefix) FROM routes_v4'),'routingPrefixesV6':scalar(db,'SELECT COUNT(DISTINCT prefix) FROM routes_v6'),'originAsns':scalar(db,'SELECT COUNT(*) FROM origin_summary'),'probeIds':scalar(db,'SELECT COUNT(DISTINCT probe_id) FROM probes'),'peeringNetworkAsns':scalar(db,'SELECT COUNT(DISTINCT asn) FROM peering WHERE asn IS NOT NULL')},'joins':{'originAsnsWithPeeringMetadata':scalar(db,'SELECT COUNT(*) FROM origin_summary o WHERE EXISTS(SELECT 1 FROM peering p WHERE p.asn=o.asn)'),'originAsnsWithProbeMetadata':scalar(db,'SELECT COUNT(*) FROM origin_summary o WHERE EXISTS(SELECT 1 FROM probes p WHERE p.asn=o.asn)'),'routingRowsWithExactAllocationPrefixV4':scalar(db,'SELECT COUNT(*) FROM routes_v4 r WHERE EXISTS(SELECT 1 FROM allocations a WHERE a.prefix=r.prefix)'),'routingRowsWithExactAllocationPrefixV6':scalar(db,'SELECT COUNT(*) FROM routes_v6 r WHERE EXISTS(SELECT 1 FROM allocations a WHERE a.prefix=r.prefix)')},'quality':{'integrity':db.execute('PRAGMA quick_check').fetchone()[0],'nonScalarOriginRows':scalar(db,'SELECT (SELECT COUNT(*) FROM routes_v4 WHERE asn IS NULL)+(SELECT COUNT(*) FROM routes_v6 WHERE asn IS NULL)'),'defaultRouteRows':scalar(db,'SELECT (SELECT COUNT(*) FROM routes_v4 WHERE plen=0)+(SELECT COUNT(*) FROM routes_v6 WHERE plen=0)'),'allocationStatuses':dict(db.execute('SELECT status,COUNT(*) FROM allocations GROUP BY status')),'exactPrefixJoinIsNotContainmentCoverage':True,'noCrossTypeDeviceTotal':True,'sourceTimesAreNotCurrentLiveness':True},'executionAdmitted':0,'networkRequestsDuringBuild':0,'truthBoundary':BOUNDARY}
def build(census:Path,routing:Path,census_sha:str,routing_sha:str,out:Path)->dict:
    started=time.monotonic();out.mkdir(parents=True,exist_ok=True);key=hashlib.sha256((VERSION+':'+census_sha+':'+routing_sha).encode()).hexdigest();dest=out/key;dest.mkdir(exist_ok=True);rp=dest/'receipt.json'
    if rp.exists():
        rec=json.loads(rp.read_text())
        if rec.get('inputHashes')!={'census':census_sha,'routing':routing_sha}:raise ValueError('BAD_RECEIPT_INPUT')
        if sha256_file(dest/'atlas.sqlite')!=rec['databaseSha256']:raise ValueError('DATABASE_SHA_MISMATCH')
        if sha256_file(census)!=census_sha or sha256_file(routing)!=routing_sha:raise ValueError('ARTIFACT_SHA_MISMATCH')
        atomic_json(out/'CURRENT.json',{'snapshot':key,'receipt':str(Path(key)/'receipt.json')})
        return {**rec,'currentInvocation':{'reused':True,'elapsedSeconds':round(time.monotonic()-started,3),'newRows':0,'networkRequests':0}}
    with verify_zip(census,census_sha) as c,verify_zip(routing,routing_sha) as r:
        cm,rm=decode(c.read('manifest.json')),decode(r.read('manifest.json'))
        if cm.get('schema')!='deus-global-passive-internet-census/1' or rm.get('schema')!='deus-global-routing-overlay/1':raise ValueError('UNSUPPORTED_INPUT_SCHEMA')
        db=sqlite3.connect(dest/'atlas.sqlite')
        try:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL');db.execute('PRAGMA cache_size=-65536');db.executescript(SCHEMA);stages=[]
            for s in STAGES:
                result=import_stage(db,c if s[4]=='census' else r,s);stages.append(result);print(json.dumps(result),flush=True)
            db.executescript(INDEXES);metrics=report(db)
            expected={'allocations':cm['rir']['descriptorRecords'],'asn_ranges':cm['rir']['asnRecords'],'peering':cm['topology']['peeringDbEntities'],'probes':cm['observedDevices']['ripeAtlasRecords'],'routes_v4':rm['ipv4Rows'],'routes_v6':rm['ipv6Rows']}
            if metrics['inputRows']!=expected:raise ValueError('SOURCE_ROW_COUNT_MISMATCH')
            if metrics['quality']['integrity']!='ok':raise ValueError('DATABASE_INTEGRITY_FAILURE')
            db.commit();db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally:db.close()
    rec={'schema':VERSION,'snapshot':key,'generatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'inputHashes':{'census':census_sha,'routing':routing_sha},'sourceSnapshotTimes':{'census':cm['generatedAt'],'routing':rm['generatedAt']},'databaseSha256':sha256_file(dest/'atlas.sqlite'),'databaseBytes':(dest/'atlas.sqlite').stat().st_size,'stages':stages,'metrics':metrics,'elapsedSeconds':round(time.monotonic()-started,3),'verdict':'PASS_SNAPSHOT_INDEX_ONLY'}
    atomic_json(rp,rec);atomic_json(out/'CURRENT.json',{'snapshot':key,'receipt':str(Path(key)/'receipt.json')});return rec
def query_ip(database:Path,value:str)->dict:
    addr=ipaddress.ip_address(value);ancestors=[str(ipaddress.ip_network((addr,p),strict=False)) for p in range(addr.max_prefixlen,-1,-1)];slots=','.join('?' for _ in ancestors)
    with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;routes=[dict(r) for r in db.execute(f'SELECT * FROM routes_v{addr.version} WHERE prefix IN ({slots}) ORDER BY plen DESC,asn',ancestors)];allocs=[dict(r) for r in db.execute(f'SELECT * FROM allocations WHERE prefix IN ({slots}) ORDER BY plen DESC',ancestors)];longest=[r for r in routes if r['plen']==routes[0]['plen']];asns=sorted({r['asn'] for r in longest if r['asn'] is not None});networks=[]
        for a in asns:networks += [dict(r) for r in db.execute('SELECT source_id,name,asn,status FROM peering WHERE asn=?',(a,))]
    return {'ip':str(addr),'longestObservedRoutes':longest,'coveringAllocations':allocs,'peeringNetworks':networks,'defaultRouteOnly':bool(longest) and longest[0]['plen']==0,'networkRequests':0,'executionAdmitted':False,'truthBoundary':BOUNDARY}
def main()->None:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True);b=sub.add_parser('build');b.add_argument('--census',type=Path,required=True);b.add_argument('--routing',type=Path,required=True);b.add_argument('--census-sha256',required=True);b.add_argument('--routing-sha256',required=True);b.add_argument('--out',type=Path,required=True);q=sub.add_parser('query');q.add_argument('--database',type=Path,required=True);q.add_argument('--ip',required=True);a=p.parse_args();result=build(a.census,a.routing,a.census_sha256,a.routing_sha256,a.out) if a.cmd=='build' else query_ip(a.database,a.ip);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
