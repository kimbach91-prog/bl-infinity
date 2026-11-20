import copy,importlib.util,json,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('atlas',Path(__file__).with_name('verify-public-atlas-dag.py'))
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
FIXTURE={'schema':'deus-public-atlas-ci-input/1','data_class':'PUBLIC','records':[{'source_entity':'http://www.wikidata.org/entity/Q1','label':'one','repositories':['https://github.com/example/one']},{'source_entity':'http://www.wikidata.org/entity/Q2','label':'two','repositories':['https://gitlab.com/example/two']}]}
def parts(rows):
    result=[]
    for i in range(4):
        group=rows[i::4];v=M.oracle(group);result.append({'partition':i,'records':len(group),'result':v,'digest':M.digest(v)})
    return result
class AtlasDAGTests(unittest.TestCase):
    def test_missing_partition_rejected(self):
        rows=M.validate_input(FIXTURE)
        with self.assertRaises(ValueError):M.reduce_partitions(parts(rows)[:3],rows)
    def test_tampered_partition_rejected(self):
        rows=M.validate_input(FIXTURE);p=parts(rows);p[0]['result']['host_counts']={'other.invalid':1}
        with self.assertRaises(ValueError):M.reduce_partitions(p,rows)
    def test_credential_in_url_rejected(self):
        f=copy.deepcopy(FIXTURE);f['records'][0]['repositories']=['https://user:secret@example.com/repo']
        with self.assertRaises(ValueError):M.validate_input(f)
    def test_exact_scatter_reduce_oracle(self):
        rows=M.validate_input(FIXTURE);out=M.reduce_partitions(parts(rows),rows)
        self.assertEqual(out['source_count'],2);self.assertEqual(out['host_counts'],{'github.com':1,'gitlab.com':1})
if __name__=='__main__':unittest.main()
