import json
import os
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

KAGGLE = os.environ.get("KAGGLE_BIN", "/tmp/kvenv/bin/kaggle")
PORT = int(os.environ.get("PORT", "8080"))
ARC_KERNEL = os.environ.get("ARC_KERNEL_HANDLE", "lmkimbch/deus-arc-agi3-flash-next-mtp-c8-full-r2/2")
STAGE = os.environ.get("DEUS_VIDEO_V2_STAGE", "PROBE").upper()
GPU_PROBE_KERNEL = os.environ.get("DEUS_VIDEO_V2_GPU_PROBE_KERNEL", "lmkimbch/deus-video-v2-gpu-probe")
WORK = Path("/tmp/deus-video-v2")

state = {
    "service": "deus-cpu-executor-b",
    "stage": STAGE,
    "kaggle_token_bound": bool(os.environ.get("KAGGLE_API_TOKEN")),
    "drive_principal_email": None,
    "quota": None,
    "mine": None,
    "arc_kernel": ARC_KERNEL,
    "arc_status": None,
    "gpu_probe_kernel": GPU_PROBE_KERNEL,
    "gpu_probe_status": None,
    "gpu_probe_receipt": None,
    "probe_complete": False,
    "error": None,
}

def emit(event, **payload):
    print(json.dumps({"event": event, **payload}, sort_keys=True), flush=True)

def run(args, timeout=120):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=os.environ.copy())
    return {
        "ok": p.returncode == 0,
        "code": p.returncode,
        "stdout": (p.stdout or "")[:20000],
        "stderr": (p.stderr or "")[:8000],
    }

def safe_drive_principal():
    raw = os.environ.get("DEUS_GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        email = data.get("client_email")
        return email if isinstance(email, str) and "@" in email else None
    except Exception:
        return None

def probe():
    try:
        state["drive_principal_email"] = safe_drive_principal()
        q = run([KAGGLE, "quota", "-v"], timeout=90)
        state["quota"] = q
        mine = run([KAGGLE, "kernels", "list", "-m", "--page-size", "5", "-v"], timeout=90)
        state["mine"] = mine
        state["probe_complete"] = bool(q["ok"] and mine["ok"])
        emit(
            "deus_video_v2_actuator_probe",
            stage=STAGE,
            kaggle_token_bound=state["kaggle_token_bound"],
            drive_principal_email=state["drive_principal_email"],
            quota_ok=q["ok"],
            quota_stdout=q["stdout"],
            mine_ok=mine["ok"],
            mine_stdout=mine["stdout"],
        )
    except Exception as exc:
        state["error"] = f"{type(exc).__name__}:{exc}"
        emit("deus_video_v2_actuator_probe_error", error=state["error"])

def build_gpu_probe_kernel():
    root = WORK / "gpu-probe"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    code = r'''import json, os, pathlib, subprocess, sys, time
receipt = {
    "schema": "deus-video-v2-gpu-probe/1",
    "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "python": sys.version,
}
try:
    import torch
    receipt["torch"] = torch.__version__
    receipt["cuda_available"] = bool(torch.cuda.is_available())
    receipt["cuda_version"] = torch.version.cuda
    receipt["device_count"] = int(torch.cuda.device_count())
    if torch.cuda.is_available():
        receipt["devices"] = []
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            free_b, total_b = torch.cuda.mem_get_info(i)
            receipt["devices"].append({
                "index": i,
                "name": torch.cuda.get_device_name(i),
                "capability": list(torch.cuda.get_device_capability(i)),
                "total_memory_bytes": int(p.total_memory),
                "free_memory_bytes": int(free_b),
                "visible_total_memory_bytes": int(total_b),
            })
        try:
            receipt["bf16_supported"] = bool(torch.cuda.is_bf16_supported())
        except Exception as e:
            receipt["bf16_supported"] = None
            receipt["bf16_error"] = type(e).__name__ + ":" + str(e)
        x = torch.arange(1_000_000, dtype=torch.float32, device="cuda")
        y = (x * 1.5 + 2.0).sum()
        torch.cuda.synchronize()
        receipt["kernel_executed"] = True
        receipt["kernel_result"] = float(y.item())
    else:
        receipt["kernel_executed"] = False
except Exception as e:
    receipt["error"] = type(e).__name__ + ":" + str(e)
    receipt["kernel_executed"] = False
try:
    smi = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total,memory.free,driver_version","--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=30)
    receipt["nvidia_smi"] = smi.stdout.strip()
except Exception as e:
    receipt["nvidia_smi_error"] = type(e).__name__ + ":" + str(e)
path = pathlib.Path("/kaggle/working/DEUS_VIDEO_V2_GPU_PROBE.json")
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print("DEUS_VIDEO_V2_GPU_PROBE=" + json.dumps(receipt, sort_keys=True))
'''
    (root / "gpu_probe.py").write_text(code)
    metadata = {
        "id": GPU_PROBE_KERNEL,
        "title": "DEUS Video V2 GPU Probe",
        "code_file": "gpu_probe.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": False,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }
    (root / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return root

def fetch_gpu_probe_output():
    out = WORK / "gpu-probe-output"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    got = run([KAGGLE, "kernels", "output", GPU_PROBE_KERNEL, "-p", str(out), "-o"], timeout=600)
    if not got["ok"]:
        return {"ok": False, "download": got}
    p = out / "DEUS_VIDEO_V2_GPU_PROBE.json"
    if not p.exists():
        return {"ok": False, "reason": "receipt_missing", "files": [str(x) for x in out.rglob("*") if x.is_file()]}
    receipt = json.loads(p.read_text())
    state["gpu_probe_receipt"] = receipt
    emit("deus_video_v2_gpu_probe_receipt", kernel=GPU_PROBE_KERNEL, receipt=receipt)
    return {"ok": True, "receipt": receipt}

def gpu_probe_loop():
    root = build_gpu_probe_kernel()
    status = run([KAGGLE, "kernels", "status", GPU_PROBE_KERNEL], timeout=90)
    txt = (status["stdout"] + "\n" + status["stderr"]).upper()
    if not status["ok"] or "NOT FOUND" in txt or "404" in txt:
        push = run([KAGGLE, "kernels", "push", "-p", str(root), "--timeout", "900", "--accelerator", "gpu"], timeout=300)
        emit("deus_video_v2_gpu_probe_push", kernel=GPU_PROBE_KERNEL, ok=push["ok"], stdout=push["stdout"], stderr=push["stderr"])
        if not push["ok"]:
            state["error"] = "gpu_probe_push_failed"
            state["gpu_probe_status"] = push
            return
    while True:
        try:
            st = run([KAGGLE, "kernels", "status", GPU_PROBE_KERNEL], timeout=90)
            state["gpu_probe_status"] = st
            text_status = (st["stdout"] + "\n" + st["stderr"]).upper()
            emit("deus_video_v2_gpu_probe_poll", kernel=GPU_PROBE_KERNEL, ok=st["ok"], stdout=st["stdout"], stderr=st["stderr"])
            if st["ok"] and "COMPLETE" in text_status:
                fetch_gpu_probe_output()
                return
            if "ERROR" in text_status or "CANCEL" in text_status:
                logs = run([KAGGLE, "kernels", "logs", GPU_PROBE_KERNEL], timeout=120)
                state["error"] = "gpu_probe_runtime_error"
                emit("deus_video_v2_gpu_probe_error", logs=logs)
                return
        except Exception as exc:
            emit("deus_video_v2_gpu_probe_poll_error", error=f"{type(exc).__name__}:{exc}")
        time.sleep(20)

def arc_poll_loop():
    while True:
        try:
            r = run([KAGGLE, "kernels", "status", ARC_KERNEL], timeout=90)
            state["arc_status"] = r
            emit("arc3_c8_status_poll_preserved", kernel=ARC_KERNEL, ok=r["ok"], stdout=r["stdout"], stderr=r["stderr"])
        except Exception as exc:
            state["arc_status"] = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
        time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/video-v2-status"):
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(state, sort_keys=True).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    probe()
    threading.Thread(target=arc_poll_loop, daemon=True).start()
    if STAGE == "PUSH_GPU_PROBE":
        threading.Thread(target=gpu_probe_loop, daemon=True).start()
    emit("deus_video_v2_actuator_listening", port=PORT, stage=STAGE)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
