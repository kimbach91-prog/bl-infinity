import base64
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

KAGGLE = os.environ.get("KAGGLE_BIN", "/tmp/kvenv/bin/kaggle")
PORT = int(os.environ.get("PORT", "8080"))
ARC_KERNEL = os.environ.get("ARC_KERNEL_HANDLE", "lmkimbch/deus-arc-agi3-flash-next-mtp-c8-full-r2/2")
STAGE = os.environ.get("DEUS_VIDEO_V2_STAGE", "PROBE").upper()
GPU_PROBE_KERNEL = os.environ.get("DEUS_VIDEO_V2_GPU_PROBE_KERNEL", "lmkimbch/deus-video-v2-gpu-probe")
I2V_KERNEL = os.environ.get("DEUS_VIDEO_V2_I2V_KERNEL", "lmkimbch/deus-video-v2-i2vgenxl-r1")
INPUT_DRIVE_FILE_ID = os.environ.get("DEUS_VIDEO_V2_INPUT_DRIVE_FILE_ID", "")
ARTIFACT_CAP = os.environ.get("DEUS_VIDEO_ARTIFACT_CAP", "")
WORK = Path("/tmp/deus-video-v2")
I2V_OUT = WORK / "i2v-output"

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
    "i2v_kernel": I2V_KERNEL,
    "i2v_status": None,
    "i2v_receipt": None,
    "i2v_artifact_ready": False,
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
        "stdout": (p.stdout or "")[:30000],
        "stderr": (p.stderr or "")[:12000],
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

def download_drive_file(file_id):
    if not file_id:
        raise RuntimeError("DEUS_VIDEO_V2_INPUT_DRIVE_FILE_ID missing")
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info = json.loads(os.environ["DEUS_GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    session = AuthorizedSession(creds)
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    response = session.get(url, timeout=180)
    response.raise_for_status()
    return response.content

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

def kernel_exists(handle):
    st = run([KAGGLE, "kernels", "status", handle], timeout=90)
    text = (st["stdout"] + "\n" + st["stderr"]).upper()
    return st["ok"] and "NOT FOUND" not in text and "404" not in text, st

def build_gpu_probe_kernel():
    root = WORK / "gpu-probe"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    code = r'''import json, pathlib, subprocess, sys, time
receipt = {"schema":"deus-video-v2-gpu-probe/1","ts_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"python":sys.version}
try:
    import torch
    receipt["torch"]=torch.__version__; receipt["cuda_available"]=bool(torch.cuda.is_available())
    receipt["cuda_version"]=torch.version.cuda; receipt["device_count"]=int(torch.cuda.device_count())
    if torch.cuda.is_available():
        receipt["devices"]=[]
        for i in range(torch.cuda.device_count()):
            p=torch.cuda.get_device_properties(i); free_b,total_b=torch.cuda.mem_get_info(i)
            receipt["devices"].append({"index":i,"name":torch.cuda.get_device_name(i),"capability":list(torch.cuda.get_device_capability(i)),"total_memory_bytes":int(p.total_memory),"free_memory_bytes":int(free_b),"visible_total_memory_bytes":int(total_b)})
        receipt["bf16_supported"]=bool(torch.cuda.is_bf16_supported())
        x=torch.arange(1_000_000,dtype=torch.float32,device="cuda"); y=(x*1.5+2.0).sum(); torch.cuda.synchronize()
        receipt["kernel_executed"]=True; receipt["kernel_result"]=float(y.item())
    else: receipt["kernel_executed"]=False
except Exception as e:
    receipt["error"]=type(e).__name__+":"+str(e); receipt["kernel_executed"]=False
try:
    smi=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total,memory.free,driver_version","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=30)
    receipt["nvidia_smi"]=smi.stdout.strip()
except Exception as e: receipt["nvidia_smi_error"]=type(e).__name__+":"+str(e)
path=pathlib.Path("/kaggle/working/DEUS_VIDEO_V2_GPU_PROBE.json"); path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("DEUS_VIDEO_V2_GPU_PROBE="+json.dumps(receipt,sort_keys=True))
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
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
    }
    (root / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return root

def fetch_kernel_output(handle, out_dir, pattern=None):
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    args = [KAGGLE, "kernels", "output", handle, "-p", str(out_dir), "-o"]
    if pattern:
        args += ["--file-pattern", pattern]
    return run(args, timeout=1200)

def gpu_probe_loop():
    root = build_gpu_probe_kernel()
    exists, status = kernel_exists(GPU_PROBE_KERNEL)
    if not exists:
        push = run([KAGGLE, "kernels", "push", "-p", str(root), "--timeout", "900", "--accelerator", "gpu"], timeout=300)
        emit("deus_video_v2_gpu_probe_push", kernel=GPU_PROBE_KERNEL, ok=push["ok"], stdout=push["stdout"], stderr=push["stderr"])
        if not push["ok"]:
            state["error"]="gpu_probe_push_failed"; state["gpu_probe_status"]=push; return
    while True:
        st=run([KAGGLE,"kernels","status",GPU_PROBE_KERNEL],timeout=90); state["gpu_probe_status"]=st
        text_status=(st["stdout"]+"\n"+st["stderr"]).upper()
        emit("deus_video_v2_gpu_probe_poll",kernel=GPU_PROBE_KERNEL,ok=st["ok"],stdout=st["stdout"],stderr=st["stderr"])
        if st["ok"] and "COMPLETE" in text_status:
            out=WORK/"gpu-probe-output"; got=fetch_kernel_output(GPU_PROBE_KERNEL,out)
            p=out/"DEUS_VIDEO_V2_GPU_PROBE.json"
            if got["ok"] and p.exists():
                receipt=json.loads(p.read_text()); state["gpu_probe_receipt"]=receipt
                emit("deus_video_v2_gpu_probe_receipt",kernel=GPU_PROBE_KERNEL,receipt=receipt)
            return
        if "ERROR" in text_status or "CANCEL" in text_status:
            state["error"]="gpu_probe_runtime_error"; return
        time.sleep(20)

def build_i2v_kernel(ref_bytes):
    root = WORK / "i2v-kernel"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    ref_b64 = base64.b64encode(ref_bytes).decode("ascii")
    prompt = (
        "Photorealistic live-action single young adult woman matching the reference identity and white satin dress. "
        "She begins facing the camera with a warm playful smile, makes a tiny natural bounce, then performs one complete "
        "smooth 360-degree turn in place with believable human weight shift and small foot steps. Her long dark hair and satin "
        "dress respond naturally to inertia and gravity. She returns to face the camera, raises her right hand, waves happily, "
        "and smiles. Stable fixed camera, realistic anatomy, realistic skin and fabric, consistent face and outfit, cinematic hotel-room lighting."
    )
    negative = (
        "cartoon, anime, illustration, duplicate person, twins, extra limbs, extra fingers, missing limbs, malformed hands, "
        "face morphing, identity change, body distortion, floating, sliding without footsteps, camera orbit, sexualized pose, "
        "wardrobe change, flicker, warped background, low quality, blurry"
    )
    code = f'''import base64, hashlib, json, os, pathlib, subprocess, sys, time
from io import BytesIO

REF_B64 = {ref_b64!r}
PROMPT = {prompt!r}
NEGATIVE = {negative!r}
MODEL_ID = "ali-vilab/i2vgen-xl"
OUT = pathlib.Path("/kaggle/working")
RAW = OUT / "DEUS_NATIVE_GENERATIVE_VIDEO_V2_RAW.mp4"
FINAL = OUT / "DEUS_NATIVE_GENERATIVE_VIDEO_V2.mp4"
RECEIPT = OUT / "DEUS_NATIVE_GENERATIVE_VIDEO_V2_RECEIPT.json"

def sh(cmd):
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)

# Use current Kaggle CUDA/PyTorch and install only the inference stack.
sh([sys.executable,"-m","pip","install","-q","--upgrade",
    "diffusers>=0.37.1","transformers>=4.46","accelerate>=1.1",
    "huggingface_hub>=0.31","safetensors","imageio","imageio-ffmpeg","Pillow"])

import torch
from PIL import Image
from diffusers import I2VGenXLPipeline
from diffusers.utils import export_to_video
from huggingface_hub import snapshot_download, model_info
import imageio_ffmpeg

assert torch.cuda.is_available(), "CUDA unavailable"
device_name = torch.cuda.get_device_name(0)
free_b, total_b = torch.cuda.mem_get_info(0)

allow = [
    "model_index.json",
    "scheduler/*",
    "feature_extractor/*",
    "image_encoder/config.json",
    "image_encoder/model.fp16.safetensors",
    "text_encoder/config.json",
    "text_encoder/model.fp16.safetensors",
    "tokenizer/*",
    "unet/config.json",
    "unet/diffusion_pytorch_model.fp16.safetensors",
    "vae/config.json",
    "vae/diffusion_pytorch_model.fp16.safetensors",
]
model_dir = snapshot_download(MODEL_ID, allow_patterns=allow)
info = model_info(MODEL_ID)

primary = pathlib.Path(model_dir) / "unet" / "diffusion_pytorch_model.fp16.safetensors"
assert primary.exists(), str(primary)
h = hashlib.sha256()
with primary.open("rb") as f:
    for chunk in iter(lambda: f.read(8*1024*1024), b""):
        h.update(chunk)
checkpoint_sha = h.hexdigest()

image = Image.open(BytesIO(base64.b64decode(REF_B64))).convert("RGB").resize((384,640), Image.Resampling.LANCZOS)

pipe = I2VGenXLPipeline.from_pretrained(
    model_dir,
    torch_dtype=torch.float16,
    variant="fp16",
    local_files_only=True,
)
pipe.enable_model_cpu_offload()
if hasattr(pipe.vae, "enable_slicing"):
    pipe.vae.enable_slicing()

seed = 260923
generator = torch.Generator(device="cpu").manual_seed(seed)
start = time.time()
result = pipe(
    prompt=PROMPT,
    image=image,
    height=640,
    width=384,
    target_fps=4,
    num_frames=16,
    num_inference_steps=50,
    guidance_scale=8.0,
    negative_prompt=NEGATIVE,
    decode_chunk_size=1,
    generator=generator,
)
frames = result.frames[0]
export_to_video(frames, str(RAW), fps=4)

# Motion is learned in the 16 generated frames. This step only smooths playback.
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
try:
    sh([ffmpeg,"-y","-i",str(RAW),"-vf","minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
        "-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(FINAL)])
    interpolation = "ffmpeg_minterpolate_4_to_24fps"
except Exception as e:
    FINAL.write_bytes(RAW.read_bytes())
    interpolation = "fallback_raw_4fps:" + type(e).__name__

output_sha = hashlib.sha256(FINAL.read_bytes()).hexdigest()
receipt = {{
    "schema":"deus-native-generative-video-v2-receipt/1",
    "state":"LEARNED_I2V_EXECUTED_AND_ENCODED",
    "backend":"I2VGenXLPipeline",
    "model_id":MODEL_ID,
    "model_revision":info.sha,
    "learned_checkpoint_sha256":checkpoint_sha,
    "weights_origin":"huggingface:"+MODEL_ID,
    "weights_license":"MIT",
    "generation_operator":"diffusion",
    "temporal_latent_frames":16,
    "sampling_steps":50,
    "spatiotemporal_modeling":True,
    "primary_motion_operators":["learned_spatiotemporal_latent"],
    "postprocess":[interpolation],
    "proprietary_video_api_calls":0,
    "seed":seed,
    "prompt":PROMPT,
    "negative_prompt":NEGATIVE,
    "input_resolution":[384,640],
    "generated_frames":len(frames),
    "generated_condition_fps":4,
    "final_fps":24 if "minterpolate" in interpolation else 4,
    "gpu":device_name,
    "gpu_total_memory_bytes":int(total_b),
    "gpu_free_memory_bytes_at_start":int(free_b),
    "torch":torch.__version__,
    "cuda":torch.version.cuda,
    "runtime_seconds":round(time.time()-start,3),
    "output_file":FINAL.name,
    "output_bytes":FINAL.stat().st_size,
    "output_sha256":output_sha,
    "truth_boundary":"GENERATIVE_PROVENANCE_EXECUTED__NATURALNESS_REQUIRES_VISUAL_READBACK"
}}
RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\\n")
print("DEUS_NATIVE_GENERATIVE_VIDEO_V2_RECEIPT="+json.dumps(receipt,sort_keys=True),flush=True)
'''
    (root / "generate_i2v.py").write_text(code)
    metadata = {
        "id": I2V_KERNEL,
        "title": "DEUS Native Generative Video V2 I2VGenXL",
        "code_file": "generate_i2v.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
    }
    (root / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return root

def i2v_loop():
    try:
        ref = download_drive_file(INPUT_DRIVE_FILE_ID)
        emit("deus_video_v2_input_fetched", drive_file_id=INPUT_DRIVE_FILE_ID, bytes=len(ref), sha256=hashlib.sha256(ref).hexdigest())
        root = build_i2v_kernel(ref)
        exists, old_status = kernel_exists(I2V_KERNEL)
        should_push = not exists
        if exists:
            old_txt=(old_status["stdout"]+"\n"+old_status["stderr"]).upper()
            emit("deus_video_v2_i2v_existing_kernel", kernel=I2V_KERNEL, status=old_status)
            if "ERROR" in old_txt or "CANCEL" in old_txt:
                should_push=True
        if should_push:
            push = run([KAGGLE,"kernels","push","-p",str(root),"--timeout","7200","--accelerator","gpu"],timeout=600)
            emit("deus_video_v2_i2v_push",kernel=I2V_KERNEL,ok=push["ok"],stdout=push["stdout"],stderr=push["stderr"])
            if not push["ok"]:
                state["error"]="i2v_push_failed"; state["i2v_status"]=push; return
        while True:
            st=run([KAGGLE,"kernels","status",I2V_KERNEL],timeout=90); state["i2v_status"]=st
            txt=(st["stdout"]+"\n"+st["stderr"]).upper()
            emit("deus_video_v2_i2v_poll",kernel=I2V_KERNEL,ok=st["ok"],stdout=st["stdout"],stderr=st["stderr"])
            if st["ok"] and "COMPLETE" in txt:
                got=fetch_kernel_output(I2V_KERNEL,I2V_OUT)
                emit("deus_video_v2_i2v_output_download",kernel=I2V_KERNEL,ok=got["ok"],stdout=got["stdout"],stderr=got["stderr"])
                rp=I2V_OUT/"DEUS_NATIVE_GENERATIVE_VIDEO_V2_RECEIPT.json"
                vp=I2V_OUT/"DEUS_NATIVE_GENERATIVE_VIDEO_V2.mp4"
                if got["ok"] and rp.exists() and vp.exists():
                    receipt=json.loads(rp.read_text())
                    if hashlib.sha256(vp.read_bytes()).hexdigest()!=receipt.get("output_sha256"):
                        state["error"]="i2v_output_hash_mismatch"; return
                    state["i2v_receipt"]=receipt; state["i2v_artifact_ready"]=True
                    emit("deus_video_v2_i2v_receipt",receipt=receipt)
                else:
                    state["error"]="i2v_output_missing"
                return
            if "ERROR" in txt or "CANCEL" in txt:
                logs=run([KAGGLE,"kernels","logs",I2V_KERNEL],timeout=180)
                state["error"]="i2v_runtime_error"
                emit("deus_video_v2_i2v_error",logs=logs)
                return
            time.sleep(30)
    except Exception as exc:
        state["error"]=f"i2v_loop:{type(exc).__name__}:{exc}"
        emit("deus_video_v2_i2v_exception",error=state["error"])

def arc_poll_loop():
    while True:
        try:
            r=run([KAGGLE,"kernels","status",ARC_KERNEL],timeout=90)
            state["arc_status"]=r
            emit("arc3_c8_status_poll_preserved",kernel=ARC_KERNEL,ok=r["ok"],stdout=r["stdout"],stderr=r["stderr"])
        except Exception as exc:
            state["arc_status"]={"ok":False,"error":f"{type(exc).__name__}:{exc}"}
        time.sleep(60)

def cap_ok(path):
    if not ARTIFACT_CAP:
        return False
    q=urllib.parse.urlparse(path)
    return urllib.parse.parse_qs(q.query).get("cap",[None])[0] == ARTIFACT_CAP

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path)
        if parsed.path in ("/health","/video-v2-status"):
            body=json.dumps(state,sort_keys=True).encode()
            self.send_response(200); self.send_header("content-type","application/json"); self.send_header("content-length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        if parsed.path == "/video-v2-artifact":
            if not cap_ok(self.path) or not state.get("i2v_artifact_ready"):
                self.send_response(404); self.end_headers(); return
            p=I2V_OUT/"DEUS_NATIVE_GENERATIVE_VIDEO_V2.mp4"
            body=p.read_bytes(); self.send_response(200); self.send_header("content-type","video/mp4"); self.send_header("content-length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        if parsed.path == "/video-v2-receipt":
            if not cap_ok(self.path) or not state.get("i2v_artifact_ready"):
                self.send_response(404); self.end_headers(); return
            p=I2V_OUT/"DEUS_NATIVE_GENERATIVE_VIDEO_V2_RECEIPT.json"
            body=p.read_bytes(); self.send_response(200); self.send_header("content-type","application/json"); self.send_header("content-length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()
    def log_message(self,*args): pass

if __name__=="__main__":
    WORK.mkdir(parents=True,exist_ok=True)
    probe()
    threading.Thread(target=arc_poll_loop,daemon=True).start()
    if STAGE=="PUSH_GPU_PROBE": threading.Thread(target=gpu_probe_loop,daemon=True).start()
    if STAGE=="PUSH_I2VGENXL": threading.Thread(target=i2v_loop,daemon=True).start()
    emit("deus_video_v2_actuator_listening",port=PORT,stage=STAGE)
    HTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
