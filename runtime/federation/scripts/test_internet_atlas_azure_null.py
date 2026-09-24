import copy,json,tempfile,unittest
from pathlib import Path
import internet_atlas_azure as m
from test_internet_atlas_azure import BASE,NOW,PAGE,raw,fetch

class NullableFeatureTests(unittest.TestCase):
    def test_null_network_features_is_empty_optional_list(self):
        o=copy.deepcopy(BASE);o['values'][0]['properties']['networkFeatures']=None
        rows,_=m.parse_payload(raw(o))
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['meta']['networkFeatures'],[])
    def test_missing_network_features(self):
        o=copy.deepcopy(BASE);del o['values'][0]['properties']['networkFeatures']
        self.assertEqual(m.parse_payload(raw(o))[0][0]['meta']['networkFeatures'],[])
    def test_invalid_feature_type_not_silently_admitted(self):
        o=copy.deepcopy(BASE);o['values'][0]['properties']['networkFeatures']='not-a-list'
        with self.assertRaises(ValueError):m.parse_payload(raw(o))
    def test_known_legacy_parser_failure_can_retry_once_after_repair(self):
        with tempfile.TemporaryDirectory() as p:
            hp=Path(p)/'azure.hold.json';hp.write_text(json.dumps({'retryEpoch':NOW+m.TTL,'error':"TypeError:'NoneType' object is not iterable",'dataFreshnessNotAdvanced':True}))
            source,r=m.refresh(p,NOW,fetch,minimum=1)
            self.assertIsNotNone(source);self.assertEqual(r['networkRequests'],2)
            self.assertEqual(r['retryReason'],'NULLABLE_FEATURE_PARSER_REPAIRED')
    def test_provider_rate_limit_backoff_is_never_parser_bypassed(self):
        with tempfile.TemporaryDirectory() as p:
            hp=Path(p)/'azure.hold.json';hp.write_text(json.dumps({'retryEpoch':NOW+m.TTL,'error':'HTTPError:HTTP Error 429: Too Many Requests','dataFreshnessNotAdvanced':True}))
            def forbidden(*args):raise AssertionError('provider backoff must hold')
            source,r=m.refresh(p,NOW,forbidden,minimum=1)
            self.assertIsNone(source);self.assertEqual(r['networkRequests'],0)
    def test_same_version_failure_does_not_repeat(self):
        with tempfile.TemporaryDirectory() as p:
            hp=Path(p)/'azure.hold.json';hp.write_text(json.dumps({'retryEpoch':NOW+m.TTL,'error':"TypeError:'NoneType' object is not iterable",'parserVersion':m.VERSION}))
            def forbidden(*args):raise AssertionError('same version must hold')
            source,r=m.refresh(p,NOW,forbidden,minimum=1)
            self.assertIsNone(source);self.assertEqual(r['networkRequests'],0)

if __name__=='__main__':unittest.main()
