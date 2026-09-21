import json, os, tempfile, unittest
from pathlib import Path
import importlib.util

P=Path(__file__).with_name("kaggle_actuator.py")
spec=importlib.util.spec_from_file_location("act",P); act=importlib.util.module_from_spec(spec); spec.loader.exec_module(act)

class T(unittest.TestCase):
    def good(self):
        return {
            "competition":act.COMPETITION,
            "notebook_ref":"owner/candidate",
            "exact_notebook_version":1,
            "candidate_sha256":"a"*64,
            "submission_file":"submission.parquet",
            "audit_passed":True,
            "non_dominated":True,
            "incumbent_protection_ack":True,
            "promotion_gate":"PASS",
        }
    def test_good(self): self.assertTrue(act.validate_manifest(self.good()))
    def test_fail_closed_each_gate(self):
        for k in ["audit_passed","non_dominated","incumbent_protection_ack"]:
            m=self.good(); m[k]=False
            with self.assertRaises(ValueError): act.validate_manifest(m)
        m=self.good();m["promotion_gate"]="HOLD"
        with self.assertRaises(ValueError): act.validate_manifest(m)
        m=self.good();m["exact_notebook_version"]=0
        with self.assertRaises(ValueError): act.validate_manifest(m)
    def test_no_secret_echo_contract(self):
        keys=set(act.auth_presence())
        self.assertEqual(keys,{"token","classic_pair","json_file"})

if __name__=="__main__": unittest.main()
