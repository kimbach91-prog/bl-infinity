import copy,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
import internet_atlas_azure as m

NOW=datetime(2026,9,24,tzinfo=timezone.utc).timestamp()
URL='https://download.microsoft.com/download/a/b/c/abc-123/ServiceTags_Public_20260921.json'
PAGE=('<a href="'+URL+'">Download</a>').encode()
BASE={'cloud':'Public','changeNumber':1,'values':[{'name':'Storage.West','id':'s','properties':{'systemService':'Storage','region':'west','changeNumber':1,'networkFeatures':['API'],'addressPrefixes':['192.0.2.0/24','2001:db8::/32']}}]}
def raw(o=BASE):return json.dumps(o).encode()
def fetch(url,headers):return (200,{},PAGE if url==m.PAGE else raw())

class AzureTests(unittest.TestCase):
    def test_dual_family_and_metadata(self):
        rows,s=m.parse_payload(raw());self.assertEqual(len(rows),2);self.assertEqual(s['regions'],1)
        self.assertEqual(rows[0]['meta']['category'],'Storage.West')
    def test_same_prefix_multiple_tags_kept(self):
        o=copy.deepcopy(BASE);second=copy.deepcopy(o['values'][0]);second['name']='Other.West';o['values'].append(second)
        rows,s=m.parse_payload(raw(o));self.assertEqual(len(rows),4);self.assertEqual(s['uniquePrefixes'],2)
    def test_duplicate_full_tuple_removed(self):
        o=copy.deepcopy(BASE);o['values']*=2;self.assertEqual(len(m.parse_payload(raw(o))[0]),2)
    def test_wrong_cloud_rejected(self):
        o=copy.deepcopy(BASE);o['cloud']='Other'
        with self.assertRaises(ValueError):m.parse_payload(raw(o))
    def test_default_prefix_rejected(self):
        o=copy.deepcopy(BASE);o['values'][0]['properties']['addressPrefixes']=['0.0.0.0/0']
        with self.assertRaises(ValueError):m.parse_payload(raw(o))
    def test_noncanonical_prefix_rejected(self):
        o=copy.deepcopy(BASE);o['values'][0]['properties']['addressPrefixes']=['192.0.2.1/24']
        with self.assertRaises(ValueError):m.parse_payload(raw(o))
    def test_link_allowlist(self):
        self.assertTrue(m.valid_payload_url(URL))
        for u in [URL.replace('https:','http:'),URL.replace('download.microsoft.com','download.microsoft.com.attacker.invalid'),URL+'?token=secret',URL.replace('https://','https://user:pw@')]:
            self.assertFalse(m.valid_payload_url(u))
    def test_link_selection_and_age(self):
        u,d,age=m.discover(PAGE,NOW);self.assertEqual((u,d,age),(URL,'2026-09-21',3))
    def test_future_link_rejected(self):
        with self.assertRaises(ValueError):m.discover(PAGE.replace(b'20260921',b'20260925'),NOW)
    def test_empty_page_rejected(self):
        with self.assertRaises(ValueError):m.discover(b'no download link',NOW)
    def test_repeat_is_zero_http_and_preserves_source_time(self):
        with tempfile.TemporaryDirectory() as p:
            source,r=m.refresh(p,NOW,fetch,minimum=1);self.assertEqual(r['networkRequests'],2)
            def forbidden(*args):raise AssertionError('network must not run')
            again,rr=m.refresh(p,NOW+1,forbidden,minimum=1)
            self.assertEqual(rr['networkRequests'],0);self.assertEqual(source,again)
    def test_failure_keeps_last_good_and_backoff(self):
        with tempfile.TemporaryDirectory() as p:
            source,_=m.refresh(p,NOW,fetch,minimum=1)
            def bad(*args):raise OSError('offline')
            held,r=m.refresh(p,NOW+m.TTL+1,bad,minimum=1)
            self.assertEqual(source,held);self.assertEqual(r['state'],'HOLD_LAST_GOOD')
            held2,r2=m.refresh(p,NOW+m.TTL+2,bad,minimum=1);self.assertEqual(r2['networkRequests'],0)
    def test_tampered_cache_rejected(self):
        with tempfile.TemporaryDirectory() as p:
            m.refresh(p,NOW,fetch,minimum=1);f=Path(p)/'azure.json';o=json.loads(f.read_text());o['rows']=[];f.write_text(json.dumps(o))
            with self.assertRaises(ValueError):m.refresh(p,NOW+1,fetch,minimum=1)
    def test_stale_publication_not_labeled_recent(self):
        oldpage=PAGE.replace(b'20260921',b'20260721')
        def older(url,headers):return 200,{},oldpage if url==m.PAGE else raw()
        with tempfile.TemporaryDirectory() as p:
            source,_=m.refresh(p,NOW,older,minimum=1)
            self.assertEqual(source['publicationFreshness'],'STALE_PUBLISHED_DATE_NOT_CURRENT')
    def test_version_regression_held(self):
        with tempfile.TemporaryDirectory() as p:
            source,_=m.refresh(p,NOW,fetch,minimum=1)
            o=copy.deepcopy(BASE);o['changeNumber']=0
            def older(url,headers):return 200,{},PAGE if url==m.PAGE else raw(o)
            held,r=m.refresh(p,NOW+m.TTL+1,older,minimum=1);self.assertEqual(held,source);self.assertEqual(r['state'],'HOLD_LAST_GOOD')

if __name__=='__main__':unittest.main()
