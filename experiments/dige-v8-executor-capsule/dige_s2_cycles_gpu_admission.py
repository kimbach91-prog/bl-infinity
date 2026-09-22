import bpy, json, hashlib, os, pathlib, subprocess, sys, threading, time

def sh(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()

def gpu_rows():
    q=["nvidia-smi","--query-gpu=index,name,uuid,driver_version,memory.total,memory.used,memory.free",
       "--format=csv,noheader,nounits"]
    rows=[]
    for line in sh(q).splitlines():
        p=[x.strip() for x in line.split(",")]
        if len(p)>=7:
            rows.append({
                "index":int(p[0]),"name":p[1],"uuid":p[2],"driver":p[3],
                "total_mb":int(float(p[4])),"used_mb":int(float(p[5])),"free_mb":int(float(p[6]))
            })
    return rows

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
outdir=pathlib.Path(args[0] if args else "runtime/gpu_admission").resolve()
outdir.mkdir(parents=True,exist_ok=True)
png=outdir/"DIGE_S2_GPU_CANARY.png"
receipt_path=outdir/"DIGE_S2_GPU_ADMISSION_RECEIPT.json"

before=gpu_rows()
if not before:
    raise RuntimeError("NVIDIA telemetry unavailable; fail closed")

scene=bpy.context.scene
if not scene.camera:
    raise RuntimeError("S2 scene camera missing")
if not any(o.type=="MESH" and not o.hide_render for o in scene.objects):
    raise RuntimeError("No renderable S2 mesh in current scene")

prefs=bpy.context.preferences.addons["cycles"].preferences
selected_backend=None
errors=[]
for backend in ("CUDA","OPTIX"):
    try:
        prefs.compute_device_type=backend
        prefs.get_devices()
        usable=[]
        for d in prefs.devices:
            use=(d.type==backend and any(str(g["name"]).lower() in d.name.lower() or d.name.lower() in str(g["name"]).lower() for g in before))
            d.use=bool(use)
            if use: usable.append({"name":d.name,"type":d.type,"id":getattr(d,"id",None)})
        if usable:
            selected_backend=backend
            enabled=usable
            break
    except Exception as e:
        errors.append({"backend":backend,"error":repr(e)})
if not selected_backend:
    raise RuntimeError("No attributable NVIDIA Cycles device enabled: "+json.dumps(errors))

scene.render.engine="BLENDER_EEVEE_NEXT" if False else "CYCLES"
scene.cycles.device="GPU"
scene.cycles.samples=4
scene.render.resolution_x=96
scene.render.resolution_y=96
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(png)

samples=[]
stop=False
def poll():
    while not stop:
        try:
            samples.append({"t":time.time(),"gpus":gpu_rows()})
        except Exception as e:
            samples.append({"t":time.time(),"error":repr(e)})
        time.sleep(.20)

t=threading.Thread(target=poll,daemon=True)
t.start()
started=time.time()
render_error=None
try:
    bpy.ops.render.render(write_still=True)
except Exception as e:
    render_error=repr(e)
finally:
    elapsed=time.time()-started
    stop=True
    t.join(timeout=2.0)
after=gpu_rows()

if render_error:
    raise RuntimeError("Cycles GPU render failed: "+render_error)
if not png.exists() or png.stat().st_size==0:
    raise RuntimeError("Cycles GPU canary output missing")

peak={}
for s in samples:
    for g in s.get("gpus",[]):
        key=g["uuid"]
        cur=peak.setdefault(key,{"name":g["name"],"uuid":key,"total_mb":g["total_mb"],"max_used_mb":0,"min_free_mb":g["free_mb"]})
        cur["max_used_mb"]=max(cur["max_used_mb"],g["used_mb"])
        cur["min_free_mb"]=min(cur["min_free_mb"],g["free_mb"])

telemetry_ok=bool(peak) and all(v["total_mb"]>0 and v["max_used_mb"]>0 for v in peak.values())
receipt={
    "schema":"deus-dige-s2-cycles-gpu-admission/1",
    "workload_class":"BLENDER_CYCLES_S2_RENDER_CANARY",
    "state":"EXECUTED_AND_TELEMETERED" if telemetry_ok else "EXECUTED_TELEMETRY_INCOMPLETE",
    "backend":selected_backend,
    "enabled_devices":enabled,
    "before":before,
    "after":after,
    "poll_samples":len(samples),
    "peak":list(peak.values()),
    "elapsed_seconds":elapsed,
    "render":{"file":png.name,"sha256":sha256(png),"bytes":png.stat().st_size,"samples":4,"resolution":[96,96]},
    "strict_gpu_credit_candidate":len(enabled) if telemetry_ok else 0,
    "strict_visible_vram_gb_candidate":sum(v["total_mb"] for v in peak.values())/1024.0 if telemetry_ok else 0,
    "promotion_gate":"CANON_READBACK_REQUIRED",
    "truth_boundary":"THIS_RECEIPT_ADMITS_ONLY_BLENDER_CYCLES_S2_RENDER_CLASS; IT DOES_NOT PROVE ARBITRARY CUDA, CONCURRENCY, SLA OR GLOBAL VRAM POOL"
}
receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
