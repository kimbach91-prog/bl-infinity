from __future__ import annotations
import asyncio, io, json, pathlib, tarfile
from inspect_ai.util._sandbox.context import cleanup_sandbox_environments_sample, init_sandbox_environments_sample
from inspect_ai.util._sandbox.docker.docker import DockerSandboxEnvironment
import apn.checker as checker_mod
from apn.checker import SandboxComparator
from apn.dataset import ERDOS_DIR, fc_commit
from apn.task import get_compose_file

SPEC_PATH=pathlib.Path("apn/data/erdos/Isolated/Erdos242.erdos_242.lean")
DECL="Erdos242.erdos_242"
TASK="deus_erdos242_comparator"

def tar_of(text:str)->bytes:
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w") as tf:
        data=text.encode()
        i=tarfile.TarInfo("Spec.lean"); i.size=len(data)
        tf.addfile(i,io.BytesIO(data))
    return b.getvalue()

async def main():
    spec=SPEC_PATH.read_text()
    proof='''by
  intro h
  have h3 := h 3 (by norm_num)
  rcases h3 with ⟨x, y, z, hx, hxy, hyz, heq⟩
  norm_num at heq
'''
    needle=f"theorem {DECL}.disproof : ¬ (type_of% @{DECL}) := sorry"
    replacement=f"theorem {DECL}.disproof : ¬ (type_of% @{DECL}) := {proof}"
    if needle not in spec:
        raise RuntimeError("target disproof declaration not found")
    submission=spec.replace(needle,replacement)
    pin=fc_commit(ERDOS_DIR)
    compose=str(get_compose_file(pin,literature=False))
    await DockerSandboxEnvironment.task_init(TASK,compose)
    try:
      envs=await init_sandbox_environments_sample(
        sandboxenv_type=DockerSandboxEnvironment,task_name=TASK,config=compose,files={},setup=None,metadata={})
      try:
        env=envs["comparator"]
        checker_mod.sandbox=lambda *a,**k: env
        out=await SandboxComparator().check(spec,tar_of(submission),decl=DECL,claim="disproof")
        receipt={"schema":"DEUS_FRONTIERMATH_ERDOS242_COMPARATOR_V1","pin":pin,"decl":DECL,"claim":"disproof","ok":out.ok,"stage":out.stage,"detail_tail":out.detail[-4000:]}
        pathlib.Path("deus-erdos242-comparator-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(json.dumps(receipt,sort_keys=True))
        if not out.ok: raise SystemExit(2)
      finally:
        await cleanup_sandbox_environments_sample(type="docker",task_name=TASK,config=compose,environments=envs,interrupted=False)
    finally:
      await DockerSandboxEnvironment.task_cleanup(TASK,compose,cleanup=True)
asyncio.run(main())
