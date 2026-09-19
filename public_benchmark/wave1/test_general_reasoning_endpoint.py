#!/usr/bin/env python3
import json, pathlib, subprocess, tempfile, sys
root=pathlib.Path(__file__).resolve().parent
task={
 "task_id":"CANARY-GRE-001","benchmark":"synthetic-contract-canary","benchmark_version":"1",
 "task_ref":"local:opaque","allowed_tools":[],"budget":{"seconds":5},
 "evaluator_ref":"local:deterministic","authority_ref":"owner:test"
}
with tempfile.TemporaryDirectory() as td:
 d=pathlib.Path(td)
 p=d/"task.json"; p.write_text(json.dumps(task))
 out=d/"receipt.json"

 r=subprocess.run([sys.executable,str(root/"general_reasoning_endpoint.py"),"--task",str(p),"--out",str(out)],capture_output=True,text=True)
 if r.returncode!=3:
     raise AssertionError({"phase":"no-solver","returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr})
 x=json.loads(out.read_text())
 assert x["execution_state"]=="HOLD_NO_BOUND_SOLVER_COMMAND", x

 solver=d/"canary_solver.py"
 solver.write_text("print('CANARY_SOLVED')\n")
 argv=d/"solver_argv.json"
 argv.write_text(json.dumps([sys.executable,str(solver)]))
 r=subprocess.run([sys.executable,str(root/"general_reasoning_endpoint.py"),"--task",str(p),"--solver-argv-file",str(argv),"--out",str(out)],capture_output=True,text=True)
 if r.returncode!=0:
     raise AssertionError({"phase":"solver","returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr})
 x=json.loads(out.read_text())
 assert x["execution_state"]=="EXECUTED", x
 assert x["result_digest"], x
 result=json.loads((d/"general-reasoning-result.json").read_text())
 assert result["stdout"].strip()=="CANARY_SOLVED", result
 assert result["returncode"]==0, result
 print("GENERAL_REASONING_ENDPOINT_CONTRACT_CANARY=PASS")
