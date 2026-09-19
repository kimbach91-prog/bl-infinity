#!/usr/bin/env python3
import json, pathlib, subprocess, tempfile, sys
root=pathlib.Path(__file__).resolve().parent
task={
 "task_id":"CANARY-GRE-001","benchmark":"synthetic-contract-canary","benchmark_version":"1",
 "task_ref":"local:opaque","allowed_tools":[],"budget":{"seconds":5},
 "evaluator_ref":"local:deterministic","authority_ref":"owner:test"
}
with tempfile.TemporaryDirectory() as d:
 d=pathlib.Path(d)
 p=d/"task.json"; p.write_text(json.dumps(task))
 out=d/"receipt.json"

 # Gate A: endpoint must fail closed when no semantic solver is bound.
 r=subprocess.run([sys.executable,str(root/"general_reasoning_endpoint.py"),"--task",str(p),"--out",str(out)],capture_output=True,text=True)
 assert r.returncode==3, (r.returncode, r.stdout, r.stderr)
 x=json.loads(out.read_text())
 assert x["execution_state"]=="HOLD_NO_BOUND_SOLVER_COMMAND"

 # Gate B: use a real temporary solver file instead of shell-quote-sensitive python -c.
 solver=d/"canary_solver.py"
 solver.write_text("print('CANARY_SOLVED')\n")
 cmd=f'{sys.executable} {solver}'
 r=subprocess.run([sys.executable,str(root/"general_reasoning_endpoint.py"),"--task",str(p),"--solver-cmd",cmd,"--out",str(out)],capture_output=True,text=True)
 assert r.returncode==0, (r.returncode, r.stdout, r.stderr)
 x=json.loads(out.read_text())
 assert x["execution_state"]=="EXECUTED"
 assert x["result_digest"]
 result=json.loads((d/"general-reasoning-result.json").read_text())
 assert result["stdout"].strip()=="CANARY_SOLVED"
 assert result["returncode"]==0
 print("GENERAL_REASONING_ENDPOINT_CONTRACT_CANARY=PASS")
