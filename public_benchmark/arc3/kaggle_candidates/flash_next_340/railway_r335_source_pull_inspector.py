#!/usr/bin/env python3
"""Read-only inspect latest Kaggle kernel source for R335 state candidate.

No push/run/submit. Pulls source+metadata for the latest state kernel and emits
only bounded code snippets around R335 patch markers plus notebook/source hashes.
"""
from __future__ import annotations
import hashlib, http.server, json, os, shutil, socketserver, subprocess, threading
from pathlib import Path

REF="lmkimbch/deus-arc3-r338-state-tr87"
ROOT=Path("/tmp/deus-r335-source-pull")

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"ok\n"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*args): pass

def health():
    socketserver.TCPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),H).serve_forever()

def emit(ev,d):
    print(ev+" "+json.dumps(d,sort_keys=True,separators=(",",":")),flush=True)

def run(cmd,timeout=180,check=True):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"{Path(cmd[0]).name}:rc{p.returncode}:{(p.stderr or '')[-500:]}")
    return p

def main():
    threading.Thread(target=health,daemon=True).start()
    if ROOT.exists(): shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    try:
        q=run(["kaggle","kernels","pull",REF,"-p",str(ROOT),"-m"],timeout=180,check=False)
        emit("DEUS_R335_SOURCE_PULL",{"rc":q.returncode,"stdout":(q.stdout or "")[-800:],"stderr":(q.stderr or "")[-800:],"kernel_push":False,"competition_submission":False})
        if q.returncode: raise RuntimeError("kernel_pull_failed")
        files=[]
        for f in sorted(ROOT.rglob("*")):
            if f.is_file():
                files.append({"path":str(f.relative_to(ROOT)),"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()})
        emit("DEUS_R335_SOURCE_FILES",{"files":files[:30]})
        notebooks=list(ROOT.glob("*.ipynb"))
        if len(notebooks)!=1: raise RuntimeError(f"notebook_count:{len(notebooks)}")
        nb=json.loads(notebooks[0].read_text(encoding="utf-8"))
        hits=[]
        for i,cell in enumerate(nb.get("cells",[])):
            if cell.get("cell_type")!="code": continue
            src="".join(cell.get("source",[]))
            if "R335_STRUCTURED_STATE" in src or "patch_tool_agent_r335" in src or "_agent_patched" in src:
                lines=src.splitlines()
                selected=[]
                for n,line in enumerate(lines,1):
                    if any(k in line for k in ("R335_","patch_tool_agent_r335","_agent_state_patched","_agent_patched")):
                        selected.append({"line":n,"text":line[:1000]})
                hits.append({"cell":i,"sha256":hashlib.sha256(src.encode()).hexdigest(),"selected":selected[:80]})
        emit("DEUS_R335_SOURCE_MARKERS",{"hits":hits})
    except Exception as e:
        emit("DEUS_R335_SOURCE_PULL_HOLD",{"code":type(e).__name__,"detail":str(e)[:500],"kernel_push":False,"competition_submission":False})
    threading.Event().wait()

if __name__=="__main__": main()
