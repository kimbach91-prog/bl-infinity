import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import internet_atlas_cloud_delta as m

class TestCloudDelta(unittest.TestCase):
    def test_multiple_services_are_not_lost(self):
        b=json.dumps({'prefixes':[{'ip_prefix':'8.0.0.0/8','service':'EC2'},{'ip_prefix':'8.0.0.0/8','service':'AMAZON'},{'ip_prefix':'8.0.0.0/8','service':'EC2'}]}).encode()
        self.assertEqual(len(m.parse('aws',b)),2)
    def test_strict_cidr_rejects_host_bits(self):
        with self.assertRaises(ValueError):m.parse('lines',b'8.8.8.8/24')
    def test_default_route_held(self):
        with self.assertRaises(ValueError):m.parse('lines',b'0.0.0.0/0')
    def test_ipv6_projection(self):
        self.assertEqual(m.projection('2001:db8::/32')[:3],('2001:db8::/32',32,6))
    def test_oracle_tag_group_not_cartesian(self):
        b=json.dumps({'regions':[{'region':'eu-test-1','cidrs':[{'cidr':'8.0.0.0/8','tags':['OSN','OBJECT_STORAGE']}]}]}).encode()
        r=m.parse('oracle',b);self.assertEqual(len(r),1);self.assertEqual(r[0]['meta']['tags'],['OBJECT_STORAGE','OSN'])
    def test_atlassian_dimensions(self):
        b=json.dumps({'items':[{'cidr':'8.0.0.0/8','product':['jira','confluence'],'direction':['egress','ingress']}]}).encode()
        r=m.parse('atlassian',b);self.assertEqual(len(r),1);self.assertEqual(len(r[0]['meta']['product']),2)
    def test_github_metadata_not_domains(self):
        b=json.dumps({'api':['8.0.0.0/8'],'domains':['https://example.com/a'],'verifiable_password_authentication':True}).encode()
        self.assertEqual(len(m.parse('github',b)),1)
    def test_public_ssh_keys_are_not_ip_ranges(self):
        b=json.dumps({'ssh_keys':['ecdsa-sha2-nistp256 AAAA/public/key=='],'api':['8.0.0.0/8']}).encode()
        self.assertEqual(len(m.parse('github',b)),1)
    def test_failed_source_backoff_without_data(self):
        with tempfile.TemporaryDirectory() as d:
            spec=('X','https://example.com','lines',1,100)
            m.refresh(spec,d,now=1,fetcher=lambda u,h:(503,{},b''))
            a,r=m.refresh(spec,d,now=2,fetcher=lambda u,h:self.fail('must respect backoff'))
            self.assertIsNone(a);self.assertEqual(r['networkRequests'],0)
    def test_list_metadata_sql_adapter(self):
        self.assertEqual(m.sql_scalar(['x','y']),'["x","y"]')
    def test_fastly(self):
        self.assertEqual(len(m.parse('fastly',b'{"addresses":["8.0.0.0/8"],"ipv6_addresses":["2001:db8::/32"]}')),2)
    def test_google(self):
        self.assertEqual(m.parse('google',b'{"prefixes":[{"ipv4Prefix":"8.0.0.0/8","scope":"global"}]}')[0]['meta']['scope'],'global')
    def test_refresh_then_skip(self):
        with tempfile.TemporaryDirectory() as d:
            s=('A','https://example.com/list','lines',1,100)
            a,r=m.refresh(s,d,now=1000,fetcher=lambda u,h:(200,{'ETag':'x'},b'8.0.0.0/8'))
            b,q=m.refresh(s,d,now=1050,fetcher=lambda u,h:self.fail('unexpected network'))
            self.assertEqual(a,b);self.assertEqual(q['networkRequests'],0)
    def test_304(self):
        with tempfile.TemporaryDirectory() as d:
            s=('A','https://example.com/list','lines',1,100)
            a,_=m.refresh(s,d,now=1000,fetcher=lambda u,h:(200,{'ETag':'x'},b'8.0.0.0/8'))
            def f(u,h):self.assertEqual(h['If-None-Match'],'x');return 304,{},b''
            b,r=m.refresh(s,d,now=1200,fetcher=f);self.assertEqual(a['rows'],b['rows']);self.assertEqual(r['state'],'UNCHANGED_304')
    def test_empty_keeps_good(self):
        with tempfile.TemporaryDirectory() as d:
            s=('A','https://example.com/list','lines',1,100)
            a,_=m.refresh(s,d,now=1000,fetcher=lambda u,h:(200,{},b'8.0.0.0/8'))
            b,r=m.refresh(s,d,now=1200,fetcher=lambda u,h:(200,{},b''))
            self.assertEqual(a['rows'],b['rows']);self.assertEqual(a['observedAt'],b['observedAt']);self.assertEqual(r['state'],'HELD_LAST_GOOD')
    def test_tampered_source_cache(self):
        with tempfile.TemporaryDirectory() as d:
            s=('A','https://example.com/list','lines',1,100)
            a,_=m.refresh(s,d,now=1000,fetcher=lambda u,h:(200,{},b'8.0.0.0/8'))
            a['rows']=[];m.atomic(Path(d)/'A.json',a)
            with self.assertRaises(ValueError):m.refresh(s,d,now=1001)
    def test_invalid_304_without_cache(self):
        with tempfile.TemporaryDirectory() as d:
            a,r=m.refresh(('A','https://example.com','lines',1,100),d,now=1,fetcher=lambda u,h:(304,{},b''))
            self.assertIsNone(a);self.assertEqual(r['state'],'HELD_NO_SNAPSHOT')
    def test_family_failure_does_not_discard_other(self):
        with tempfile.TemporaryDirectory() as d:
            good,_=m.refresh(('A','https://example.com','lines',1,100),d,now=1,fetcher=lambda u,h:(200,{},b'8.0.0.0/8'))
            bad,_=m.refresh(('B','https://example.net','lines',1,100),d,now=1,fetcher=lambda u,h:(503,{},b''))
            self.assertIsNotNone(good);self.assertIsNone(bad)
    def test_same_sql_scan_index_equivalence(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE cloud_prefixes(source TEXT,prefix TEXT,service TEXT,region TEXT,scope TEXT,category TEXT,metadata_json TEXT);CREATE INDEX cloud_prefixes_prefix ON cloud_prefixes(prefix);')
        db.executemany('INSERT INTO cloud_prefixes VALUES(?,?,?,?,?,?,?)',[('A','8.0.0.0/8','X',None,None,None,'{}'),('B','8.8.0.0/16','Y',None,None,None,'{}'),('A','2001:db8::/32','X',None,None,None,'{}')])
        for ip in ['8.8.8.8','1.1.1.1','2001:db8::1']:
            self.assertEqual(m.lookup(db,ip,True),m.lookup(db,ip,False))
        self.assertEqual(len(m.lookup(db,'8.8.8.8')),2)

if __name__=='__main__':unittest.main()
