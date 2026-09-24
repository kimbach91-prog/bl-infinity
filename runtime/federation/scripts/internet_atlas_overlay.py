#!/usr/bin/env python3
"""Build/query a small immutable overlay over the joined public Internet atlas.

Consumes only digest-bound same-repository artifacts already collected by DEUS.
No host probing, DNS lookup, network access, liveness inference, or execution admission.
"""
from __future__ import annotations
import argparse, hashlib, ipaddress, json, os, re, sqlite3, time, zipfile
from datetime import datetime, timezone
from pathlib import Path

VERSION='internet-atlas-overlay/1.0.0'
BOUNDARY='PUBLIC_SOURCE_SNAPSHOT_RELATIONS_ONLY; NO_DNS_OR_HOST_PROBING; NO_LIVENESS; NO_CONTROL; NO_EXECUTION_AUTHORITY; NO_GLOBAL_COMPLETENESS'

SCHEMA='''
CREATE TABLE IF NOT EXISTS source_inputs(name TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL, manifest_schema TEXT, generated_at TEXT, manifest_digest TEXT);
CREATE TABLE IF NOT EXISTS cloud_prefixes(
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, prefix TEXT NOT NULL, plen INTEGER NOT NULL, family INTEGER NOT NULL,
  resource_key TEXT, slot_id TEXT, service TEXT, region TEXT, scope TEXT, category TEXT, metadata_json TEXT
);
CREATE TABLE IF NOT EXISTS peering_memberships(
  id INTEGER PRIMARY KEY, relation TEXT NOT NULL, asn INTEGER, ix_id INTEGER, ixlan_id INTEGER, ix_name TEXT, ip TEXT,
  from_resource_key TEXT, to_resource_key TEXT
);
CREATE TABLE IF NOT EXISTS root_ns_relations(
  id INTEGER PRIMARY KEY, zone TEXT NOT NULL, ns TEXT NOT NULL, from_resource_key TEXT, to_resource_key TEXT
);
CREATE TABLE IF NOT EXISTS rpki_validation_samples(
  id INTEGER PRIMARY KEY, prefix TEXT NOT NULL, plen INTEGER NOT NULL, family INTEGER NOT NULL, origin_asn INTEGER,
  status TEXT NOT NULL, matched_vrp_len INTEGER, max_length INTEGER, covering_vrp_len INTEGER,
  prefix_resource_key TEXT, asn_resource_key TEXT
);
CREATE TABLE IF NOT EXISTS ct_certificates(
  cert_sha256 TEXT PRIMARY KEY, resource_key TEXT NOT NULL, operator TEXT, log_id TEXT, log_url TEXT,
  entry_index INTEGER, entry_type TEXT, subject TEXT, issuer TEXT, valid_from TEXT, valid_to TEXT
);
CREATE TABLE IF NOT EXISTS ct_domains(
  resource_key TEXT PRIMARY KEY, domain TEXT NOT NULL, operator TEXT, log_id TEXT, log_url TEXT, entry_index INTEGER
);
CREATE TABLE IF NOT EXISTS ct_relations(
  id INTEGER PRIMARY KEY, cert_resource_key TEXT NOT NULL, domain_resource_key TEXT NOT NULL,
  cert_sha256 TEXT NOT NULL, domain TEXT NOT NULL, operator TEXT, log_id TEXT, log_url TEXT,
  entry_index INTEGER, entry_type TEXT, observed_at TEXT
);
'''
INDEXES='''
CREATE INDEX IF NOT EXISTS cloud_prefixes_prefix ON cloud_prefixes(prefix);
CREATE INDEX IF NOT EXISTS cloud_prefixes_source ON cloud_prefixes(source);
CREATE INDEX IF NOT EXISTS peering_memberships_asn ON peering_memberships(asn);
CREATE INDEX IF NOT EXISTS peering_memberships_ix ON peering_memberships(ix_id,ixlan_id);
CREATE INDEX IF NOT EXISTS root_ns_zone ON root_ns_relations(zone);
CREATE INDEX IF NOT EXISTS root_ns_ns ON root_ns_relations(ns);
CREATE INDEX IF NOT EXISTS rpki_sample_prefix_asn ON rpki_validation_samples(prefix,origin_asn);
CREATE INDEX IF NOT EXISTS rpki_sample_asn ON rpki_validation_samples(origin_asn);
CREATE INDEX IF NOT EXISTS ct_domains_domain ON ct_domains(domain);
CREATE INDEX IF NOT EXISTS ct_relations_domain ON ct_relations(domain);
CREATE INDEX IF NOT EXISTS ct_relations_cert ON ct_relations(cert_sha256);
'''

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def atomic_json(p:Path,obj)->None:
    tmp=p.with_suffix(p.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2,sort_keys=True,ensure_ascii=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,p)

def verify_zip(p:Path,expected:str)->zipfile.ZipFile:
    if not re.fullmatch(r'[0-9a-f]{64}',expected): raise ValueError('EXPECTED_SHA256_REQUIRED')
    got=sha256_file(p)
    if got!=expected: raise ValueError(f'ARTIFACT_SHA_MISMATCH:{p.name}:{got}')
    z=zipfile.ZipFile(p)
    names=z.namelist()
    if len(names)!=len(set(names)): raise ValueError('DUPLICATE_ZIP_MEMBER')
    if sum(x.file_size for x in z.infolist())>1024**3: raise ValueError('EXPANDED_SIZE_LIMIT')
    return z

def rows(z:zipfile.ZipFile,name:str):
    with z.open(name) as f:
        for i,line in enumerate(f,1):
            if len(line)>1024*1024: raise ValueError(f'ROW_TOO_LARGE:{name}:{i}')
            if line.strip(): yield json.loads(line)

def manifest(z:zipfile.ZipFile)->dict:
    return json.loads(z.read('manifest.json'))

def parse_prefix(value:str):
    n=ipaddress.ip_network(value,strict=True)
    return str(n),n.prefixlen,n.version

def parse_asn(value):
    if value is None:return None
    m=re.fullmatch(r'(?:AS)?([0-9]+)',str(value).strip(),re.I)
    if not m:return None
    n=int(m.group(1)); return n if 0<=n<2**32 else None

def ancestors(value:str):
    a=ipaddress.ip_address(value)
    return [str(ipaddress.ip_network((a,p),strict=False)) for p in range(a.max_prefixlen,-1,-1)]

def insert_many(db,sql,iterable,batch=5000):
    buf=[]; total=0
    for row in iterable:
        buf.append(row)
        if len(buf)>=batch:
            db.executemany(sql,buf); total+=len(buf);buf.clear()
    if buf: db.executemany(sql,buf);total+=len(buf)
    return total

def build(*,base_db:Path,base_receipt:Path,real_zip:Path,real_sha:str,rpki_zip:Path,rpki_sha:str,ct_zip:Path,ct_sha:str,out:Path):
    started=time.monotonic()
    base_rec=json.loads(base_receipt.read_text())
    if sha256_file(base_db)!=base_rec.get('databaseSha256'): raise ValueError('BASE_DATABASE_SHA_MISMATCH')
    input_hashes={'baseDatabase':base_rec['databaseSha256'],'realMember':real_sha,'bgpRpki':rpki_sha,'ctStratified':ct_sha}
    key=hashlib.sha256((VERSION+':'+':'.join(input_hashes.values())).encode()).hexdigest()
    out.mkdir(parents=True,exist_ok=True); dest=out/key; dest.mkdir(exist_ok=True); rp=dest/'receipt.json'; dbp=dest/'overlay.sqlite'
    if rp.exists():
        rec=json.loads(rp.read_text())
        if rec.get('inputHashes')!=input_hashes: raise ValueError('BAD_OVERLAY_RECEIPT_INPUT')
        if sha256_file(dbp)!=rec.get('overlaySha256'): raise ValueError('OVERLAY_SHA_MISMATCH')
        atomic_json(out/'OVERLAY_CURRENT.json',{'snapshot':key,'receipt':str(Path(key)/'receipt.json')})
        return {**rec,'currentInvocation':{'reused':True,'elapsedSeconds':round(time.monotonic()-started,3),'newRows':0,'networkRequests':0}}
    with verify_zip(real_zip,real_sha) as rz, verify_zip(rpki_zip,rpki_sha) as bz, verify_zip(ct_zip,ct_sha) as cz:
        rm,bm,cm=manifest(rz),manifest(bz),manifest(cz)
        expected={'deus-global-internet-real-member-expansion/1','deus-global-bgp-rpki-relation-join/1','deus-global-ct-stratified-member/1'}
        got={rm.get('schema'),bm.get('schema'),cm.get('schema')}
        if got!=expected: raise ValueError(f'UNSUPPORTED_OVERLAY_INPUT_SCHEMAS:{got}')
        if rm.get('registry',{}).get('executionAdmitted',0)!=0 or bm.get('registry',{}).get('executionAdmitted',0)!=0 or cm.get('registry',{}).get('executionAdmitted',0)!=0:
            raise ValueError('UNEXPECTED_EXECUTION_ADMISSION')
        db=sqlite3.connect(dbp)
        try:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL');db.executescript(SCHEMA)
            inputs=[('realMember',real_sha,rm.get('schema'),rm.get('generatedAt'),rm.get('digest') or rm.get('manifestDigest')),('bgpRpki',rpki_sha,bm.get('schema'),bm.get('generatedAt'),bm.get('manifestDigest')),('ctStratified',ct_sha,cm.get('schema'),cm.get('generatedAt'),cm.get('manifestDigest'))]
            db.executemany('INSERT INTO source_inputs VALUES (?,?,?,?,?)',inputs)
            def cloud_rows():
                for i,r in enumerate(rows(rz,'cloud-prefixes.jsonl'),1):
                    p,l,v=parse_prefix(r['prefix']); meta=r.get('meta') or r.get('metadata') or {}
                    yield (i,r.get('source'),p,l,v,r.get('resourceKey'),str(r.get('slotId')) if r.get('slotId') is not None else None,meta.get('service'),meta.get('region'),meta.get('scope'),meta.get('category'),json.dumps(meta,sort_keys=True,separators=(',',':')))
            cloud=insert_many(db,'INSERT INTO cloud_prefixes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',cloud_rows())
            def peer_rows():
                for i,r in enumerate(rows(rz,'peering-relations.jsonl'),1):
                    yield (i,r.get('relation'),parse_asn(r.get('asn')),r.get('ixId'),r.get('ixlanId'),r.get('ixName'),r.get('ip'),r.get('fromResourceKey'),r.get('toResourceKey'))
            peering=insert_many(db,'INSERT INTO peering_memberships VALUES (?,?,?,?,?,?,?,?,?)',peer_rows())
            def ns_rows():
                for i,r in enumerate(rows(rz,'root-ns-relations.jsonl'),1):
                    yield (i,str(r.get('zone','')).lower(),str(r.get('ns','')).lower(),r.get('fromResourceKey'),r.get('toResourceKey'))
            rootns=insert_many(db,'INSERT INTO root_ns_relations VALUES (?,?,?,?,?)',ns_rows())
            def rpki_rows():
                for i,r in enumerate(rows(bz,'samples.jsonl'),1):
                    p,l,v=parse_prefix(r['prefix'])
                    yield (i,p,l,v,parse_asn(r.get('origin')),r.get('status'),r.get('matchedVrpLen'),r.get('maxLength'),r.get('coveringVrpLen'),r.get('prefixResourceKey'),r.get('asnResourceKey'))
            rpki=insert_many(db,'INSERT INTO rpki_validation_samples VALUES (?,?,?,?,?,?,?,?,?,?,?)',rpki_rows())
            def cert_rows():
                seen=set()
                for r in rows(cz,'certificates.jsonl'):
                    h=r.get('certSha256')
                    if not h or h in seen: continue
                    seen.add(h); m=r.get('meta') or {}
                    yield (h,r.get('resourceKey'),m.get('operator'),m.get('logId'),m.get('logUrl'),m.get('entryIndex'),m.get('entryType'),m.get('subject'),m.get('issuer'),m.get('validFrom'),m.get('validTo'))
            certs=insert_many(db,'INSERT INTO ct_certificates VALUES (?,?,?,?,?,?,?,?,?,?,?)',cert_rows())
            def domain_rows():
                seen=set()
                for r in rows(cz,'domains.jsonl'):
                    k=r.get('resourceKey')
                    if not k or k in seen:continue
                    seen.add(k);m=r.get('meta') or {}
                    yield (k,str(r.get('domain') or r.get('value') or '').lower(),m.get('operator'),m.get('logId'),m.get('logUrl'),m.get('entryIndex'))
            domains=insert_many(db,'INSERT INTO ct_domains VALUES (?,?,?,?,?,?)',domain_rows())
            def relation_rows():
                seen=set();i=0
                for r in rows(cz,'relations.jsonl'):
                    sig=(r.get('certResourceKey'),r.get('domainResourceKey'),r.get('logId'),r.get('entryIndex'))
                    if sig in seen:continue
                    seen.add(sig);i+=1
                    yield (i,r.get('certResourceKey'),r.get('domainResourceKey'),r.get('certSha256'),str(r.get('domain','')).lower(),r.get('operator'),r.get('logId'),r.get('logUrl'),r.get('entryIndex'),r.get('entryType'),r.get('observedAt'))
            relations=insert_many(db,'INSERT INTO ct_relations VALUES (?,?,?,?,?,?,?,?,?,?,?)',relation_rows())
            db.executescript(INDEXES);db.commit();integrity=db.execute('PRAGMA quick_check').fetchone()[0];db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally: db.close()
    counts={'cloudPrefixes':cloud,'peeringMembershipRelations':peering,'rootNsRelations':rootns,'rpkiValidationSamples':rpki,'ctCertificates':certs,'ctDomains':domains,'ctRelations':relations}
    rec={'schema':VERSION,'snapshot':key,'generatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'inputHashes':input_hashes,'sourceSnapshots':{'base':base_rec.get('generatedAt'),'realMember':rm.get('generatedAt'),'bgpRpki':bm.get('generatedAt'),'ctStratified':cm.get('generatedAt')},'counts':counts,'quality':{'integrity':integrity,'relationRows':sum([peering,rootns,rpki,relations]),'baseDatabaseReused':True,'baseRowsCopied':0,'noNetworkRequestsDuringBuild':True},'overlaySha256':sha256_file(dbp),'overlayBytes':dbp.stat().st_size,'elapsedSeconds':round(time.monotonic()-started,3),'executionAdmitted':0,'verdict':'PASS_OFFLINE_OVERLAY_ONLY','truthBoundary':BOUNDARY}
    atomic_json(rp,rec);atomic_json(out/'OVERLAY_CURRENT.json',{'snapshot':key,'receipt':str(Path(key)/'receipt.json')});return rec

def base_query_ip(base_db:Path,value:str):
    a=ipaddress.ip_address(value); aa=ancestors(value);qmarks=','.join('?'*len(aa)); table=f'routes_v{a.version}'
    with sqlite3.connect(f'file:{base_db}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        routes=[dict(x) for x in db.execute(f'SELECT * FROM {table} WHERE prefix IN ({qmarks}) ORDER BY plen DESC,asn',aa)]
        allocs=[dict(x) for x in db.execute(f'SELECT * FROM allocations WHERE prefix IN ({qmarks}) ORDER BY plen DESC',aa)]
        longest=[x for x in routes if routes and x['plen']==routes[0]['plen']]
        asns=sorted({x['asn'] for x in longest if x['asn'] is not None})
        peers=[]
        for n in asns: peers.extend(dict(x) for x in db.execute('SELECT source_id,name,asn,status,country,resource_key FROM peering WHERE asn=?',(n,)))
    return {'longestObservedRoutes':longest,'coveringAllocations':allocs,'peeringNetworks':peers,'defaultRouteOnly':bool(longest) and longest[0]['plen']==0}

def resolve_ip(base_db:Path,overlay_db:Path,value:str):
    a=ipaddress.ip_address(value); aa=ancestors(value);qm=','.join('?'*len(aa));base=base_query_ip(base_db,value)
    with sqlite3.connect(f'file:{overlay_db}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        cloud=[dict(x) for x in db.execute(f'SELECT source,prefix,plen,family,resource_key,slot_id,service,region,scope,category FROM cloud_prefixes WHERE prefix IN ({qm}) ORDER BY plen DESC,source',aa)]
        rpki=[]
        for route in base['longestObservedRoutes']:
            if route.get('asn') is None:continue
            rpki.extend(dict(x) for x in db.execute('SELECT prefix,origin_asn,status,matched_vrp_len,max_length,covering_vrp_len,prefix_resource_key,asn_resource_key FROM rpki_validation_samples WHERE prefix=? AND origin_asn=?',(route['prefix'],route['asn'])))
    return {'schema':'deus-internet-atlas-resolution/1','kind':'ip','value':str(a),**base,'publishedServiceRanges':cloud,'sparseBgpRpkiEvidence':rpki,'networkRequests':0,'executionAdmitted':False,'truthBoundary':BOUNDARY}

def resolve_asn(base_db:Path,overlay_db:Path,value):
    a=parse_asn(value)
    if a is None:raise ValueError('INVALID_ASN')
    with sqlite3.connect(f'file:{base_db}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        regs=[dict(x) for x in db.execute('SELECT first_asn,last_asn,registry,country,status,source_date FROM asn_ranges WHERE first_asn<=? AND last_asn>=? ORDER BY (last_asn-first_asn),first_asn LIMIT 16',(a,a))]
        networks=[dict(x) for x in db.execute('SELECT entity_type,source_id,name,asn,status,country,resource_key FROM peering WHERE asn=?',(a,))]
        probes=dict(db.execute('SELECT COUNT(*) n, COUNT(DISTINCT probe_id) u FROM probes WHERE asn=?',(a,)).fetchone())
        route_counts={'ipv4':db.execute('SELECT COUNT(*) FROM routes_v4 WHERE asn=?',(a,)).fetchone()[0],'ipv6':db.execute('SELECT COUNT(*) FROM routes_v6 WHERE asn=?',(a,)).fetchone()[0]}
    with sqlite3.connect(f'file:{overlay_db}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        memberships=[dict(x) for x in db.execute('SELECT relation,asn,ix_id,ixlan_id,ix_name,ip,from_resource_key,to_resource_key FROM peering_memberships WHERE asn=? ORDER BY ix_id,relation',(a,))]
        rpki=[dict(x) for x in db.execute('SELECT status,COUNT(*) count FROM rpki_validation_samples WHERE origin_asn=? GROUP BY status ORDER BY status',(a,))]
    return {'schema':'deus-internet-atlas-resolution/1','kind':'asn','value':'AS'+str(a),'registrationRanges':regs,'peeringNetworks':networks,'peeringMemberships':memberships,'probeObservationRows':probes['n'],'distinctProbeIds':probes['u'],'observedRouteRows':route_counts,'sparseBgpRpkiStatusCounts':rpki,'networkRequests':0,'executionAdmitted':False,'truthBoundary':BOUNDARY}

def resolve_domain(overlay_db:Path,value:str):
    d=str(value).strip().lower().rstrip('.')
    if not d or '/' in d or ' ' in d:raise ValueError('INVALID_DOMAIN')
    with sqlite3.connect(f'file:{overlay_db}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        rels=[dict(x) for x in db.execute('SELECT cert_resource_key,domain_resource_key,cert_sha256,domain,operator,log_id,log_url,entry_index,entry_type,observed_at FROM ct_relations WHERE domain=? ORDER BY observed_at DESC,cert_sha256',(d,))]
        certs=[];seen=set()
        for r in rels:
            if r['cert_sha256'] in seen:continue
            seen.add(r['cert_sha256'])
            c=db.execute('SELECT cert_sha256,resource_key,operator,log_id,log_url,entry_index,entry_type,subject,issuer,valid_from,valid_to FROM ct_certificates WHERE cert_sha256=?',(r['cert_sha256'],)).fetchone()
            if c:certs.append(dict(c))
    return {'schema':'deus-internet-atlas-resolution/1','kind':'domain','value':d,'ctRelations':rels,'certificates':certs,'networkRequests':0,'executionAdmitted':False,'truthBoundary':BOUNDARY}

def main():
    p=argparse.ArgumentParser(description=__doc__);sp=p.add_subparsers(dest='cmd',required=True)
    b=sp.add_parser('build')
    for name in ['base-db','base-receipt','real-zip','real-sha256','rpki-zip','rpki-sha256','ct-zip','ct-sha256','out']: b.add_argument('--'+name,required=True)
    q=sp.add_parser('resolve');q.add_argument('--base-db',required=True);q.add_argument('--overlay-db',required=True);q.add_argument('--kind',choices=['ip','asn','domain'],required=True);q.add_argument('--value',required=True)
    a=p.parse_args()
    if a.cmd=='build': result=build(base_db=Path(a.base_db),base_receipt=Path(a.base_receipt),real_zip=Path(a.real_zip),real_sha=a.real_sha256,rpki_zip=Path(a.rpki_zip),rpki_sha=a.rpki_sha256,ct_zip=Path(a.ct_zip),ct_sha=a.ct_sha256,out=Path(a.out))
    elif a.kind=='ip':result=resolve_ip(Path(a.base_db),Path(a.overlay_db),a.value)
    elif a.kind=='asn':result=resolve_asn(Path(a.base_db),Path(a.overlay_db),a.value)
    else:result=resolve_domain(Path(a.overlay_db),a.value)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
