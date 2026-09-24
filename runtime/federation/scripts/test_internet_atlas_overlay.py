import hashlib, json, sqlite3, tempfile, unittest, zipfile
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
MODULE=HERE/'internet_atlas_overlay.py'
spec=importlib.util.spec_from_file_location('overlay',MODULE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jline(x):return json.dumps(x,separators=(',',':'))+'\n'
def make_zip(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items():z.writestr(n,v if isinstance(v,(bytes,str)) else json.dumps(v))
    return sha(path)
class OverlayTest(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.base=self.root/'base.sqlite'
        db=sqlite3.connect(self.base)
        db.executescript('''
        CREATE TABLE allocations(id INTEGER PRIMARY KEY,prefix TEXT,plen INTEGER,family INTEGER,registry TEXT,country TEXT,status TEXT,source_date TEXT,descriptor_digest TEXT);
        CREATE TABLE asn_ranges(id INTEGER PRIMARY KEY,first_asn INTEGER,last_asn INTEGER,registry TEXT,country TEXT,status TEXT,source_date TEXT);
        CREATE TABLE peering(id INTEGER PRIMARY KEY,entity_type TEXT,source_id INTEGER,name TEXT,asn INTEGER,status TEXT,country TEXT,resource_key TEXT);
        CREATE TABLE probes(id INTEGER PRIMARY KEY,probe_id TEXT,family INTEGER,asn INTEGER,source_status TEXT,declared_prefix TEXT,resource_key TEXT);
        CREATE TABLE routes_v4(id INTEGER PRIMARY KEY,prefix TEXT,plen INTEGER,asn INTEGER,origin_raw TEXT,ris_peers INTEGER,relation_key TEXT);
        CREATE TABLE routes_v6(id INTEGER PRIMARY KEY,prefix TEXT,plen INTEGER,asn INTEGER,origin_raw TEXT,ris_peers INTEGER,relation_key TEXT);
        ''')
        db.execute("INSERT INTO allocations VALUES(1,'1.1.1.0/24',24,4,'apnic','AU','assigned','20110811','d')")
        db.execute("INSERT INTO asn_ranges VALUES(1,13335,13335,'arin','US','assigned','20100714')")
        db.execute("INSERT INTO peering VALUES(1,'net',4224,'Cloudflare',13335,'ok',NULL,'pk')")
        db.execute("INSERT INTO probes VALUES(1,'p1',4,13335,'Connected','1.1.1.0/24','pr')")
        db.execute("INSERT INTO routes_v4 VALUES(1,'1.1.1.0/24',24,13335,'AS13335',10,'r')")
        db.commit();db.close()
        self.base_receipt=self.root/'base-receipt.json';self.base_receipt.write_text(json.dumps({'databaseSha256':sha(self.base),'generatedAt':'2026-09-24T00:00:00Z'}))
        self.real=self.root/'real.zip';self.real_sha=make_zip(self.real,{
          'manifest.json':{'schema':'deus-global-internet-real-member-expansion/1','generatedAt':'2026-09-24T01:00:00Z','registry':{'executionAdmitted':0}},
          'cloud-prefixes.jsonl':jline({'source':'CLOUDFLARE_IPV4','prefix':'1.1.1.0/24','resourceKey':'c','slotId':'1','meta':{'service':'DNS','region':'GLOBAL'}}),
          'peering-relations.jsonl':jline({'relation':'PEERINGDB_ASN_PRESENT_AT_IXLAN','asn':'AS13335','ixId':1,'ixlanId':1,'ixName':'IX','fromResourceKey':'a','toResourceKey':'i'}),
          'root-ns-relations.jsonl':jline({'zone':'com','ns':'a.gtld-servers.net','fromResourceKey':'z','toResourceKey':'n'})})
        self.rpki=self.root/'rpki.zip';self.rpki_sha=make_zip(self.rpki,{
          'manifest.json':{'schema':'deus-global-bgp-rpki-relation-join/1','generatedAt':'2026-09-24T02:00:00Z','registry':{'executionAdmitted':0}},
          'samples.jsonl':jline({'prefix':'1.1.1.0/24','origin':'AS13335','status':'VALID_AUTHORIZED','matchedVrpLen':24,'maxLength':24,'coveringVrpLen':None,'prefixResourceKey':'p','asnResourceKey':'a'})})
        self.ct=self.root/'ct.zip';self.ct_sha=make_zip(self.ct,{
          'manifest.json':{'schema':'deus-global-ct-stratified-member/1','generatedAt':'2026-09-24T03:00:00Z','registry':{'executionAdmitted':0}},
          'certificates.jsonl':jline({'certSha256':'f'*64,'resourceKey':'cr','meta':{'operator':'O','logId':'L','logUrl':'https://ct.example','entryIndex':1,'entryType':'x509_entry','subject':'CN=example.com','issuer':'CA','validFrom':'a','validTo':'b'}}),
          'domains.jsonl':jline({'resourceKey':'dr','domain':'example.com','meta':{'operator':'O','logId':'L','logUrl':'https://ct.example','entryIndex':1}}),
          'relations.jsonl':jline({'certResourceKey':'cr','domainResourceKey':'dr','certSha256':'f'*64,'domain':'example.com','operator':'O','logId':'L','logUrl':'https://ct.example','entryIndex':1,'entryType':'x509_entry','observedAt':'2026-09-24T03:00:00Z'})})
        self.out=self.root/'out'
    def tearDown(self):self.t.cleanup()
    def build(self):return m.build(base_db=self.base,base_receipt=self.base_receipt,real_zip=self.real,real_sha=self.real_sha,rpki_zip=self.rpki,rpki_sha=self.rpki_sha,ct_zip=self.ct,ct_sha=self.ct_sha,out=self.out)
    def overlay_db(self,rec):return self.out/rec['snapshot']/'overlay.sqlite'
    def test_build_and_reuse(self):
        r=self.build();self.assertEqual(r['verdict'],'PASS_OFFLINE_OVERLAY_ONLY');self.assertEqual(r['executionAdmitted'],0);self.assertEqual(r['counts']['cloudPrefixes'],1)
        r2=self.build();self.assertTrue(r2['currentInvocation']['reused']);self.assertEqual(r2['currentInvocation']['networkRequests'],0)
    def test_resolve_ip(self):
        r=self.build();q=m.resolve_ip(self.base,self.overlay_db(r),'1.1.1.1');self.assertEqual(q['longestObservedRoutes'][0]['asn'],13335);self.assertEqual(q['publishedServiceRanges'][0]['service'],'DNS');self.assertEqual(q['sparseBgpRpkiEvidence'][0]['status'],'VALID_AUTHORIZED');self.assertFalse(q['executionAdmitted'])
    def test_resolve_asn(self):
        r=self.build();q=m.resolve_asn(self.base,self.overlay_db(r),'AS13335');self.assertEqual(q['registrationRanges'][0]['registry'],'arin');self.assertEqual(q['peeringMemberships'][0]['ix_name'],'IX');self.assertEqual(q['distinctProbeIds'],1)
    def test_resolve_domain(self):
        r=self.build();q=m.resolve_domain(self.overlay_db(r),'EXAMPLE.COM.');self.assertEqual(q['ctRelations'][0]['cert_sha256'],'f'*64);self.assertEqual(len(q['certificates']),1);self.assertEqual(q['networkRequests'],0)
if __name__=='__main__':unittest.main()
