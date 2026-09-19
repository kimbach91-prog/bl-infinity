#!/usr/bin/env python3
import json, pathlib, subprocess, tempfile, sys
root=pathlib.Path(__file__).resolve().parent
task={
 "task_id":"CANARY-GRE-001","benchmark":"synthetic-contract-canary","benchmark_version":"1",
 "task_ref":"local:opaque","allowed_tools":[],"budget":{"seconds":5},
 "evaluator_ref":"local:deterministic","authority_ref":"owner:test"
}
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/"task.json"; p.write_text(json.dumps(task))
 out=pathlib.Path(d)/"receipt.json"
 r=subprocess.run([sys.executable,str(root/"general_reasoning_endpoint.py"),"--task",str(p),"--out",str(out)],capture_output=True,text=True)
 assert r.returncode==3, (r.returncode, r.stdout, r.stderr)
 x=json.loads(out.read_text())
 assert x["execution_state"]=="HOLD_NO_BOUND_SOLVER_COMMAND"
 cmd=f'{sys.executable} -c "print(\'CANARY_SOLVED\')"'
 r=subprocess.run([sys.executable,str(root/"general_reasoning_endpoint.py"),"--task",str(p),"--solver-cmd",cmd,"--out",str(out)],capture_output=True,text=True)
 assert r.returncode==0, (r.returncode, r.stdout, r.stderr)
 x=json.loads(out.read_text())
 assert x["execution_state"]=="EXECUTED"
 assert x["result_digest"]
 print("GENERAL_REASONING_ENDPOINT_CONTRACT_CANARY=PASS")
