#!/usr/bin/env python3
"""Read-only inspector for exact R335 Flash private kernel versions.

No push/run/submit. Emits sanitized status, compact failure diagnostics, and
bounded context around the stage-1 world-model prompt in the completed baseline.
"""
from __future__ import annotations
import http.server, json, os, re, shutil, socketserver, subprocess, threading
from pathlib import Path

BASE="lmkimbch/deus-arc3-r338-base-tr87/1"
STATE="lmkimbch/deus-arc3-r338-state-tr87/3"
ROOT=Path("/tmp/r335-inspect")
ANCHOR="Maintain a compact working world model of what the current level seems to contain"

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"ok\n"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*args): pass

def health():
    socketserver.TCPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),H).serve_forever()

def emit(ev,d):
    print(ev+" "+json.dumps(d,sort_keys=True,separators=(",",":")),flush=True)

def run(cmd,timeout=180):
    return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)

def clean(text):
    text=re.sub(r'(?i)(token|key|secret|authorization|password)[=: ]+[^\s,;]+',r'\1=<redacted>',text)
    return text[:12000]

def inspect(lane,exact):
    p=run(["kaggle","kernels","status",exact],60)
    emit("DEUS_R335_KERNEL_STATUS",{"lane":lane,"exact":exact,"rc":p.returncode,"text":clean((p.stdout+"\n"+p.stderr).strip())})
    out=ROOT/lane
    out.mkdir(parents=True,exist_ok=True)
    q=run(["kaggle","kernels","output",exact,"-p",str(out)],180)
    emit("DEUS_R335_KERNEL_OUTPUT_PULL",{"lane":lane,"rc":q.returncode,"stderr":clean(q.stderr.strip())})
    files=[]
    for f in sorted(out.rglob("*")):
        if f.is_file():
            files.append({"path":str(f.relative_to(out)),"bytes":f.stat().st_size})
    emit("DEUS_R335_KERNEL_FILES",{"lane":lane,"files":files[:80]})

    if lane=="base":
        src=out/"flash_agent_overlay/inference/agent/tool_agent.py"
        if src.is_file():
            lines=src.read_text(errors="replace").splitlines()
            hits=[i for i,line in enumerate(lines) if ANCHOR in line]
            contexts=[]
            for i in hits[:5]:
                contexts.append({
                    "line_1based":i+1,
                    "before":[{"n":j+1,"repr":repr(lines[j])} for j in range(max(0,i-4),i)],
                    "line":{"n":i+1,"repr":repr(lines[i])},
                    "after":[{"n":j+1,"repr":repr(lines[j])} for j in range(i+1,min(len(lines),i+5))],
                })
            emit("DEUS_R335_BASE_PROMPT_CONTEXT",{"hits":contexts,"line_count":len(lines)})

    pats=re.compile(r"(traceback|error|exception|failed|failure|FLASH_R335|FLASH_AGENT|PUBLIC25|SyntaxError|NameError|ValueError|RuntimeError)",re.I)
    hits=[]
    for f in sorted(out.rglob("*")):
        if not f.is_file() or f.stat().st_size>40_000_000: continue
        try:t=f.read_text(errors="replace")
        except Exception:continue
        for line in t.splitlines():
            if pats.search(line):
                hits.append({"file":str(f.relative_to(out)),"line":clean(line)[:900]})
                if len(hits)>=120:break
        if len(hits)>=120:break
    emit("DEUS_R335_KERNEL_DIAGNOSTIC",{"lane":lane,"hits":hits})
    if lane=="state":
        for f in sorted(out.glob("*.log")):
            try:
                rows=json.loads(f.read_text(errors="replace"))
            except Exception:
                continue
            err=[]; started=False
            for row in rows:
                data=str(row.get("data",""))
                if "Exception encountered" in data or "Traceback (most recent call last)" in data:
                    started=True
                if started:
                    err.append(clean(data).replace("\n","\\n")[:1400])
                    if len(err)>=40: break
            emit("DEUS_R335_STATE_ERROR_CONTEXT",{"entries":err})

def main():
    threading.Thread(target=health,daemon=True).start()
    if ROOT.exists(): shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        emit("DEUS_R335_INSPECT_HOLD",{"code":"credential_absent"}); threading.Event().wait(); return
    inspect("base",BASE)
    inspect("state",STATE)
    emit("DEUS_R335_INSPECT_DONE",{"kernel_push":False,"competition_submission":False})
    threading.Event().wait()

if __name__=="__main__": main()
