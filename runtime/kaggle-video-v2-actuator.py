import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

KAGGLE = os.environ.get("KAGGLE_BIN", "/tmp/kvenv/bin/kaggle")
PORT = int(os.environ.get("PORT", "8080"))
ARC_KERNEL = os.environ.get("ARC_KERNEL_HANDLE", "lmkimbch/deus-arc-agi3-flash-next-mtp-c8-full-r2/2")
STAGE = os.environ.get("DEUS_VIDEO_V2_STAGE", "PROBE").upper()

state = {
    "service": "deus-cpu-executor-b",
    "stage": STAGE,
    "kaggle_token_bound": bool(os.environ.get("KAGGLE_API_TOKEN")),
    "drive_principal_email": None,
    "quota": None,
    "mine": None,
    "arc_kernel": ARC_KERNEL,
    "arc_status": None,
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
        "stdout": (p.stdout or "")[:12000],
        "stderr": (p.stderr or "")[:4000],
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
    probe()
    threading.Thread(target=arc_poll_loop, daemon=True).start()
    emit("deus_video_v2_actuator_listening", port=PORT, stage=STAGE)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
