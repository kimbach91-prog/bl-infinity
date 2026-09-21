import bpy, json, hashlib, os, pathlib, time

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
SHARD_ID=os.environ.get("DIGE_SAMPLE_SHARD_ID","").strip()
SAMPLES=int(os.environ.get("DIGE_SAMPLE_SHARD_SAMPLES","0") or "0")
SEED=int(os.environ.get("DIGE_SAMPLE_SHARD_SEED","0") or "0")
DEVICE_REQUESTED=os.environ.get("DIGE_CYCLES_DEVICE","CPU").strip().upper()
OUT_DIR=pathlib.Path(os.environ.get("DIGE_SHARD_OUT_DIR",str(RUNTIME/"renders"/f"c36_prebuilt_{SHARD_ID}")))
if not OUT_DIR.is_absolute():
    OUT_DIR=(ROOT/OUT_DIR).resolve()
OUT_DIR.mkdir(parents=True,exist_ok=True)

if not SHARD_ID:
    raise RuntimeError("DIGE_SAMPLE_SHARD_ID required")
if SAMPLES <= 0:
    raise RuntimeError("DIGE_SAMPLE_SHARD_SAMPLES must be >0")
if not bpy.data.filepath:
    raise RuntimeError("prebuilt .blend file must be loaded before shard script")

def sha(path):
    p=pathlib.Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def configure_device(scene):
    actual="CPU"
    devices=[]
    scene.render.engine='CYCLES'
    if DEVICE_REQUESTED=="CPU":
        scene.cycles.device='CPU'
        return {"requested":"CPU","actual":"CPU","devices":[]}
    try:
        prefs=bpy.context.preferences.addons["cycles"].preferences
        prefs.get_devices()
        candidates=[]
        for d in prefs.devices:
            dtype=str(getattr(d,"type","")).upper()
            name=str(getattr(d,"name",""))
            if dtype not in {"CPU",""}:
                candidates.append((d,dtype,name))
        if candidates:
            for d,_,_ in candidates:
                d.use=True
            scene.cycles.device='GPU'
            actual=candidates[0][1]
            devices=[{"type":t,"name":n} for _,t,n in candidates]
        else:
            scene.cycles.device='CPU'
            actual="CPU_FALLBACK"
    except Exception as error:
        scene.cycles.device='CPU'
        actual="CPU_FALLBACK"
        devices=[{"error":str(error)}]
    return {"requested":DEVICE_REQUESTED,"actual":actual,"devices":devices}

scene=bpy.context.scene
device=configure_device(scene)
scene.render.resolution_x=900
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.cycles.samples=SAMPLES
scene.cycles.seed=SEED
scene.cycles.use_denoising=False
scene.cycles.use_adaptive_sampling=False
scene.render.image_settings.media_type='IMAGE'
scene.render.image_settings.file_format='OPEN_EXR'
scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='32'

out=OUT_DIR/f"DIGE_SAMPLE_SHARD_{SHARD_ID}.exr"
scene.render.filepath=str(out)
started=time.time()
bpy.ops.render.render(write_still=True)
ended=time.time()

receipt={
  "schema":"dige-c36-prebuilt-sample-shard/1",
  "state":"EXECUTED",
  "shard_id":SHARD_ID,
  "samples":SAMPLES,
  "seed":SEED,
  "scene_file":pathlib.Path(bpy.data.filepath).name,
  "scene_sha256":sha(bpy.data.filepath),
  "output_file":out.name,
  "output_sha256":sha(out),
  "width":scene.render.resolution_x,
  "height":scene.render.resolution_y,
  "engine":scene.render.engine,
  "device":device,
  "elapsed_seconds":ended-started,
  "runner":{"name":os.environ.get("RUNNER_NAME"),"os":os.environ.get("RUNNER_OS"),"arch":os.environ.get("RUNNER_ARCH")},
  "runtime_commit":os.environ.get("DIGE_RUNTIME_COMMIT") or os.environ.get("GITHUB_SHA"),
  "truth_boundary":"SHARD_REUSES_EXACT_PREBUILT_SCENE_AND_EXECUTES_ONLY_ASSIGNED_MONTE_CARLO_SAMPLE_BUDGET__LOGICAL_MICROCELLS_NE_PHYSICAL_CORES"
}
(OUT_DIR/"DIGE_C36_SHARD_RECEIPT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
