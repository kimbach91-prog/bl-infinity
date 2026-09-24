import io,json,sqlite3,tempfile,unittest,zipfile,contextlib
from pathlib import Path
import internet_atlas_index as m
class AtlasTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def fixture(self):
  c=self.p/'c.zip';r=self.p/'r.zip'
  arrays={
   'rir-address-descriptors.jsonl':[dict(cidr='8.0.0.0/8',registry='arin',cc='US',status='allocated',executionReady=False),dict(cidr='2001:db8::/32',registry='ripencc',cc='EU',status='reserved',executionReady=False)],
   'rir-asn-records.jsonl':[dict(start='15169',value='1',registry='arin',status='allocated')],
   'peeringdb-topology.jsonl':[dict(id=1,entityType='net',asn=15169,name='Fixture',status='ok')],
   'ripe-atlas-observed-devices.jsonl':[dict(sourceId='1',identityType='ipv4',asnV4=15169,status='Disconnected',address='8.8.8.8')]
  }
  cm={'schema':'deus-global-passive-internet-census/1','generatedAt':'2020-01-01T00:00:00Z','rir':{'descriptorRecords':2,'asnRecords':1},'topology':{'peeringDbEntities':1},'observedDevices':{'ripeAtlasRecords':1}}
  with zipfile.ZipFile(c,'w') as z:
   z.writestr('manifest.json',json.dumps(cm))
   for n,rows in arrays.items():z.writestr(n,''.join(json.dumps(x)+'\n' for x in rows))
  ra={'ris-v4.jsonl':[dict(prefix='0.0.0.0/0',origin='AS1'),dict(prefix='8.8.8.0/24',origin='AS15169'),dict(prefix='8.8.8.0/24',origin='AS15170')],'ris-v6.jsonl':[dict(prefix='2001:db8::/32',origin='AS{1,2}')]}
  with zipfile.ZipFile(r,'w') as z:
   z.writestr('manifest.json',json.dumps(dict(schema='deus-global-routing-overlay/1',generatedAt='2020-01-02T00:00:00Z',ipv4Rows=3,ipv6Rows=1)))
   for n,rows in ra.items():z.writestr(n,''.join(json.dumps(x)+'\n' for x in rows))
  return c,r
 def built(self):
  c,r=self.fixture()
  with contextlib.redirect_stdout(io.StringIO()):v=m.build(c,r,m.sha256_file(c),m.sha256_file(r),self.p/'out')
  return v,self.p/'out'/v['snapshot']/'atlas.sqlite',c,r
 def test_prefixes(self):
  self.assertEqual(m.prefix_fields('2001:db8::/32'),('2001:db8::/32',32,6))
 def test_noncanonical_rejected(self):
  with self.assertRaises(ValueError):m.prefix_fields('8.8.8.1/24')
 def test_bad_asn_range(self):
  with self.assertRaises(ValueError):m.asn_range(dict(start='4294967295',value='2'),1)
 def test_nonscalar_origin_preserved(self):self.assertIsNone(m.route(dict(prefix='::/0',origin='AS{1,2}'),1)[3])
 def test_input_tamper(self):
  c,r=self.fixture()
  with self.assertRaisesRegex(ValueError,'SHA_MISMATCH'):m.verify_zip(c,'0'*64)
 def test_resume_and_idempotence(self):
  c,r=self.fixture();db=sqlite3.connect(':memory:');db.executescript(m.SCHEMA)
  with zipfile.ZipFile(c) as z:
   a=m.import_stage(db,z,m.STAGES[0],batch_size=1,stop_after=1);self.assertTrue(a['interrupted'])
   b=m.import_stage(db,z,m.STAGES[0],batch_size=1);self.assertEqual(b['resumedFrom'],1)
   d=m.import_stage(db,z,m.STAGES[0]);self.assertTrue(d['reused'])
  self.assertEqual(db.execute('SELECT COUNT(*) FROM allocations').fetchone()[0],2)
 def test_full_build_and_metrics(self):
  v,p,c,r=self.built();self.assertEqual(v['metrics']['inputRows']['routes_v4'],3);self.assertEqual(v['metrics']['quality']['nonScalarOriginRows'],1);self.assertEqual(v['metrics']['executionAdmitted'],0);self.assertEqual(v['sourceSnapshotTimes']['census'],'2020-01-01T00:00:00Z')
 def test_warm_reuse(self):
  v,p,c,r=self.built();q=m.build(c,r,m.sha256_file(c),m.sha256_file(r),self.p/'out');self.assertTrue(q['currentInvocation']['reused']);self.assertEqual(q['currentInvocation']['newRows'],0)
 def test_database_tamper(self):
  v,p,c,r=self.built()
  with p.open('ab') as f:f.write(b'tamper')
  with self.assertRaisesRegex(ValueError,'DATABASE_SHA'):m.build(c,r,m.sha256_file(c),m.sha256_file(r),self.p/'out')
 def test_lpm_multi_origin(self):
  v,p,c,r=self.built();q=m.query_ip(p,'8.8.8.8');self.assertEqual(len(q['longestObservedRoutes']),2);self.assertEqual(q['coveringAllocations'][0]['prefix'],'8.0.0.0/8');self.assertFalse(q['executionAdmitted'])
 def test_default_route_not_coverage(self):
  v,p,c,r=self.built();self.assertTrue(m.query_ip(p,'203.0.113.1')['defaultRouteOnly'])
 def test_ipv6_query(self):
  v,p,c,r=self.built();q=m.query_ip(p,'2001:db8::1');self.assertEqual(q['longestObservedRoutes'][0]['plen'],32);self.assertIsNone(q['longestObservedRoutes'][0]['asn'])
 def test_invalid_ip_rejected(self):
  with self.assertRaises(ValueError):m.query_ip(self.p/'none','https://example.com')
 def test_probe_address_omitted(self):
  row=m.probe(dict(sourceId='1',identityType='ipv4',asnV4=1,address='8.8.8.8'),1);self.assertNotIn('8.8.8.8',row)
if __name__=='__main__':unittest.main()
