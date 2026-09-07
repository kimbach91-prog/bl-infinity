#!/usr/bin/env python3
"""BL-HC-01 Huyen Co local-first provider-independent agent service.

Security posture:
- binds loopback only by default;
- no shell/eval/arbitrary URL tools;
- model endpoint comes only from local environment/config, never from request payload;
- POST requires a node-local bearer token;
- receipts contain hashes/metadata, not secrets.
"""
from __future__ import annotations
import os, json, time, hashlib, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

MAX_BODY = 262_144
HOME = Path(os.getenv('BL_HC_HOME', Path(__file__).resolve().parents[2])).resolve()
HOST = os.getenv('BL_HC_HOST', '127.0.0.1')
PORT = int(os.getenv('BL_HC_PORT', '8789'))
TOKEN = os.getenv('BL_HC_API_TOKEN', '')
MODEL_ENDPOINT = os.getenv('BL_HC_MODEL_ENDPOINT', '').rstrip('/')
MODEL_NAME = os.getenv('BL_HC_MODEL_NAME', '')
MODEL_KEY = os.getenv('BL_HC_MODEL_API_KEY', '')
TIMEOUT = float(os.getenv('BL_HC_MODEL_TIMEOUT_SEC', '120'))

if HOST not in ('127.0.0.1', '::1', 'localhost'):
    raise SystemExit('FAIL-CLOSED: BL-HC-01 service may bind loopback only in v0.1')

RECEIPTS = HOME / '05_DEUS_BRIDGE_TASKBUS' / 'receipts-local'
RECEIPTS.mkdir(parents=True, exist_ok=True)

BOOT_FILES = [
    HOME/'00_BOOT_IDENTITY'/'IDENTITY.json',
    HOME/'00_BOOT_IDENTITY'/'CURRENT.json',
    HOME/'02_CONSTITUTION_REASONING'/'COGNITIVE_CONSTITUTION.md',
    HOME/'01_MEMORY_CANON'/'MEMORY_POLICY.md',
]
CORPUS_DIRS = [HOME/'01_MEMORY_CANON', HOME/'03_RAG_CORPUS_INDEX']

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def read_text(path: Path, max_chars=60_000) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='replace')[:max_chars]
    except FileNotFoundError:
        return ''

def bootstrap_context() -> str:
    chunks=[]
    for p in BOOT_FILES:
        txt=read_text(p)
        if txt:
            chunks.append(f'### {p.name}\n{txt}')
    return '\n\n'.join(chunks)

def tokenize(s: str):
    return {w.lower().strip('.,:;!?()[]{}\"\'') for w in s.split() if len(w) >= 4}

def retrieve(query: str, limit=5):
    q=tokenize(query)
    scored=[]
    for root in CORPUS_DIRS:
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if not p.is_file() or p.suffix.lower() not in ('.md','.txt','.json'):
                continue
            if 'secret' in p.name.lower() or 'credential' in p.name.lower():
                continue
            txt=read_text(p, 24_000)
            if not txt:
                continue
            score=len(q & tokenize(txt[:12000]))
            if score:
                scored.append((score,p,txt))
    scored.sort(key=lambda x:(-x[0],str(x[1])))
    out=[]
    for score,p,txt in scored[:limit]:
        out.append({'source':str(p.relative_to(HOME)),'score':score,'text':txt[:6000]})
    return out

def model_url():
    if not MODEL_ENDPOINT:
        raise RuntimeError('BL_HC_MODEL_ENDPOINT is not configured')
    if MODEL_ENDPOINT.endswith('/chat/completions'):
        return MODEL_ENDPOINT
    return MODEL_ENDPOINT + '/chat/completions'

def call_model(messages, temperature=0.3):
    if not MODEL_NAME:
        raise RuntimeError('BL_HC_MODEL_NAME is not configured')
    payload=json.dumps({'model':MODEL_NAME,'messages':messages,'temperature':temperature}).encode()
    headers={'Content-Type':'application/json'}
    if MODEL_KEY:
        headers['Authorization']='Bearer '+MODEL_KEY
    req=urllib.request.Request(model_url(),data=payload,headers=headers,method='POST')
    with urllib.request.urlopen(req,timeout=TIMEOUT) as r:
        raw=r.read(MAX_BODY*4)
    obj=json.loads(raw)
    return obj['choices'][0]['message']['content'], obj

def receipt(task_id, request_bytes, result_text='', error=None, sources=None):
    rec={
        'schema':'BL_HC_EXECUTION_RECEIPT_V1',
        'agent_id':'BL-HC-01',
        'task_id':task_id,
        'observed_at_unix':int(time.time()),
        'request_sha256':sha256_bytes(request_bytes),
        'result_sha256':sha256_bytes(result_text.encode()) if result_text else None,
        'model_name':MODEL_NAME or None,
        'model_endpoint_configured':bool(MODEL_ENDPOINT),
        'sources':[s['source'] for s in (sources or [])],
        'error':str(error) if error else None,
        'canonical_authority':'CANDIDATE_ONLY',
        'secrets_emitted':False,
    }
    p=RECEIPTS/(task_id.replace('/','_')+'.json')
    p.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    return rec

class Handler(BaseHTTPRequestHandler):
    server_version='BL-HC-01/0.1'
    def log_message(self, fmt, *args):
        print('[BL-HC-01]', fmt%args)
    def send_json(self, code, obj):
        data=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path=='/health':
            self.send_json(200,{'ok':True,'agent_id':'BL-HC-01','host':HOST,'model_bound':bool(MODEL_ENDPOINT and MODEL_NAME),'state':'LOCAL_SERVICE_READY'})
        elif self.path=='/v1/agent/status':
            cur={}
            try: cur=json.loads(read_text(HOME/'00_BOOT_IDENTITY'/'CURRENT.json'))
            except Exception: pass
            self.send_json(200,{'agent_id':'BL-HC-01','current':cur,'model_bound':bool(MODEL_ENDPOINT and MODEL_NAME),'receipt_dir':str(RECEIPTS)})
        else: self.send_json(404,{'error':'not_found'})
    def do_POST(self):
        if not TOKEN or self.headers.get('Authorization','') != 'Bearer '+TOKEN:
            return self.send_json(401,{'error':'unauthorized'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<=0 or n>MAX_BODY: return self.send_json(413,{'error':'invalid_body_size'})
            raw=self.rfile.read(n); req=json.loads(raw)
            if self.path!='/v1/chat': return self.send_json(404,{'error':'not_found'})
            user=str(req.get('message','')).strip()
            if not user: return self.send_json(400,{'error':'message_required'})
            task_id=str(req.get('task_id') or ('blhc-'+sha256_bytes(raw)[:16]))[:100]
            sources=retrieve(user,limit=min(max(int(req.get('retrieval_k',3)),0),8))
            evidence='\n\n'.join(f"SOURCE {s['source']} score={s['score']}\n{s['text']}" for s in sources)
            system=bootstrap_context()+"\n\nYou are BL-HC-01. Use retrieved material as evidence, not automatic truth. Current instruction and reality-bound evidence override stale memory. Preserve uncertainty and provenance."
            if evidence: system+='\n\nRETRIEVED CONTEXT:\n'+evidence
            result,_=call_model([{'role':'system','content':system},{'role':'user','content':user}],float(req.get('temperature',0.3)))
            rec=receipt(task_id,raw,result_text=result,sources=sources)
            self.send_json(200,{'task_id':task_id,'agent_id':'BL-HC-01','result':result,'sources':[s['source'] for s in sources],'receipt':rec})
        except (ValueError,KeyError,json.JSONDecodeError) as e:
            self.send_json(400,{'error':'bad_request','detail':str(e)})
        except Exception as e:
            task_id='blhc-error-'+str(int(time.time()))
            receipt(task_id,b'',error=e)
            self.send_json(502,{'error':'model_or_runtime_failure','detail':str(e)})

def main():
    print(f'BL-HC-01 local service home={HOME} bind={HOST}:{PORT} model_bound={bool(MODEL_ENDPOINT and MODEL_NAME)}')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

if __name__=='__main__': main()
