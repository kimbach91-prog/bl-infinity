#!/usr/bin/env python3
import argparse, json, math, subprocess, sys
from pathlib import Path
from PIL import Image

try:
    import numpy as np
except ModuleNotFoundError:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--disable-pip-version-check", "-q", "numpy"
    ])
    import numpy as np

def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)

def region_metrics(rgb):
    h,w,_=rgb.shape
    if (w,h)!=(900,900):
        raise SystemExit(f"UNEXPECTED_IMAGE_SIZE {w}x{h}")
    y,x=np.ogrid[:h,:w]
    lum=0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2]
    face=((x-450)/145.0)**2+((y-485)/205.0)**2<=1.0
    central=face & (y>340)&(y<610)&(x>335)&(x<565)
    top=(y>235)&(y<375)&(x>315)&(x<585)
    left=(y>300)&(y<520)&(x>280)&(x<360)
    right=(y>300)&(y<520)&(x>540)&(x<620)
    dark=lum<70.0
    gx=np.abs(np.diff(lum,axis=1,prepend=lum[:,:1]))
    gy=np.abs(np.diff(lum,axis=0,prepend=lum[:1,:]))
    edge=np.hypot(gx,gy)
    return {
      "central_dark_fraction":float(dark[central].mean()),
      "central_mean_luminance":float(lum[central].mean()),
      "central_edge_mean":float(edge[central].mean()),
      "top_center_dark_fraction":float(dark[top].mean()),
      "left_side_dark_fraction":float(dark[left].mean()),
      "right_side_dark_fraction":float(dark[right].mean()),
    }

def score(m):
    symmetry=abs(m["left_side_dark_fraction"]-m["right_side_dark_fraction"])
    central=m["central_dark_fraction"]
    lum=m["central_mean_luminance"]
    top=m["top_center_dark_fraction"]
    hard=central<=0.12 and lum>=115.0 and symmetry<=0.22
    s=100.0
    s-=160.0*central
    s-=45.0*symmetry
    s-=20.0*abs(top-0.48)
    if lum<135.0: s-=0.25*(135.0-lum)
    return hard, max(-100.0,min(100.0,s)), symmetry

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--candidate-id",required=True)
    ap.add_argument("--guide-dist",required=True,type=float)
    args=ap.parse_args()
    m=region_metrics(load_rgb(args.image))
    hard,s,sym=score(m)
    out={
      "schema":"DIGE_C33_VISUAL_METRICS_V1",
      "candidate_id":args.candidate_id,
      "guide_dist_m":args.guide_dist,
      "image":Path(args.image).name,
      "hard_gate_pass":hard,
      "score":s,
      "side_symmetry_delta":sym,
      "metrics":m,
      "hard_gate":{
        "central_dark_fraction_max":0.12,
        "central_mean_luminance_min":115.0,
        "side_symmetry_delta_max":0.22
      },
      "truth_boundary":"FIXED_CAMERA_HEURISTIC_PRESELECTOR__HUMAN_FINAL_AUDIT_STILL_REQUIRED"
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
