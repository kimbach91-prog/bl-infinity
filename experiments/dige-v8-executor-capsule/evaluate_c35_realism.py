#!/usr/bin/env python3
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

LUMA=np.array([0.2126,0.7152,0.0722],dtype=np.float32)

def roi_metrics(im,box):
    a=np.asarray(im.crop(tuple(box)).convert("RGB"),dtype=np.float32)/255.0
    lum=a@LUMA
    def blur(radius):
        p=Image.fromarray(np.uint8(np.clip(lum*255,0,255)))
        return np.asarray(p.filter(ImageFilter.GaussianBlur(radius=radius)),dtype=np.float32)/255.0
    b1=blur(1.0); b4=blur(4.0)
    high=lum-b1; mid=b1-b4
    gx=np.diff(lum,axis=1); gy=np.diff(lum,axis=0)
    gm=np.sqrt(gx[:-1,:]**2+gy[:,:-1]**2)
    return {
      "lum_mean":float(lum.mean()),
      "lum_std":float(lum.std()),
      "high_rms":float(np.sqrt(np.mean(high**2))),
      "mid_rms":float(np.sqrt(np.mean(mid**2))),
      "grad_mean":float(gm.mean()),
      "grad_p90":float(np.quantile(gm,0.90)),
      "rgb_std_mean":float(a.std(axis=(0,1)).mean()),
    }

def ratio(a,b):
    return float(a/max(1e-9,b))

def clamp(x,lo,hi):
    return max(lo,min(hi,x))

def central_gate(im):
    arr=np.asarray(im.convert("RGB"),dtype=np.float32)
    lum=arr@LUMA
    h,w=lum.shape
    central=lum[int(h*.26):int(h*.67),int(w*.37):int(w*.63)]
    left=lum[int(h*.30):int(h*.65),int(w*.23):int(w*.37)]
    right=lum[int(h*.30):int(h*.65),int(w*.63):int(w*.77)]
    central_dark=float((central<55).mean())
    central_mean=float(central.mean())
    side_delta=abs(float((left<55).mean())-float((right<55).mean()))
    return {
      "central_dark_fraction":central_dark,
      "central_mean_luminance":central_mean,
      "side_symmetry_delta":side_delta,
      "pass":central_dark<=0.12 and central_mean>=115.0 and side_delta<=0.22
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True)
    ap.add_argument("--baseline",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--candidate-id",required=True)
    ap.add_argument("--branch",choices=["skin","hair","combined"],required=True)
    ap.add_argument("--profile",required=True)
    args=ap.parse_args()
    base=json.loads(Path(args.baseline).read_text())
    im=Image.open(args.image).convert("RGB")
    if list(im.size)!=base["image_size"]:
        raise SystemExit(f"IMAGE_SIZE_MISMATCH {im.size} != {base['image_size']}")
    metrics={name:roi_metrics(im,box) for name,box in base["fixed_rois"].items()}
    cg=central_gate(im)

    # Relative fixed-camera response metrics. These are optimization signals, not
    # universal photorealism certification.
    skin_rois=["forehead","cheekL","cheekR"]
    hair_rois=["hairTop","hairL","hairR"]
    skin_high=float(np.mean([ratio(metrics[k]["high_rms"],base["metrics"][k]["high_rms"]) for k in skin_rois]))
    skin_grad=float(np.mean([ratio(metrics[k]["grad_p90"],base["metrics"][k]["grad_p90"]) for k in skin_rois]))
    skin_mid=float(np.mean([ratio(metrics[k]["mid_rms"],base["metrics"][k]["mid_rms"]) for k in skin_rois]))
    skin_luma_shift=float(np.mean([abs(metrics[k]["lum_mean"]-base["metrics"][k]["lum_mean"]) for k in skin_rois]))
    # Reward visible micro/meso response but penalize excessive luminance drift or noisy overshoot.
    skin_score=100.0*(0.44*clamp(skin_high,0,2.5)+0.36*clamp(skin_grad,0,2.5)+0.20*clamp(skin_mid,0,2.2))-120.0*skin_luma_shift
    skin_sanity=all(metrics[k]["high_rms"] <= base["metrics"][k]["high_rms"]*3.2+1e-9 for k in skin_rois)

    hair_high=float(np.mean([ratio(metrics[k]["high_rms"],base["metrics"][k]["high_rms"]) for k in hair_rois]))
    hair_grad=float(np.mean([ratio(metrics[k]["grad_p90"],base["metrics"][k]["grad_p90"]) for k in hair_rois]))
    top_lum=metrics["hairTop"]["lum_mean"]
    # C34 was overly brown/bright and cap-like. A dark natural-fiber target range
    # is used only as a relative fixed-camera optimization prior.
    top_lum_penalty=abs(clamp(top_lum,0.06,0.26)-0.145)/0.115
    hair_score=100.0*(0.50*clamp(hair_high,0,2.8)+0.45*clamp(hair_grad,0,2.8)+0.05*(1.0-clamp(top_lum_penalty,0,1)))
    hair_sanity=all(metrics[k]["high_rms"] <= base["metrics"][k]["high_rms"]*3.5+1e-9 for k in hair_rois)

    branch_score={"skin":skin_score,"hair":hair_score,"combined":0.5*(skin_score+hair_score)}[args.branch]
    branch_gain={"skin":0.5*(skin_high+skin_grad),"hair":0.5*(hair_high+hair_grad),"combined":0.25*(skin_high+skin_grad+hair_high+hair_grad)}[args.branch]
    hard_pass=bool(cg["pass"] and skin_sanity and hair_sanity)
    improvement_pass=bool(hard_pass and branch_gain>=1.08)

    out={
      "schema":"DIGE_C35_REALISM_METRICS_V1",
      "candidate_id":args.candidate_id,
      "branch":args.branch,
      "profile":args.profile,
      "image":Path(args.image).name,
      "baseline_sha256":base["denoised_sha256"],
      "hard_gate_pass":hard_pass,
      "improvement_pass":improvement_pass,
      "branch_score":branch_score,
      "branch_gain":branch_gain,
      "skin_score":skin_score,
      "hair_score":hair_score,
      "skin_response":{"high_gain":skin_high,"grad_gain":skin_grad,"mid_gain":skin_mid,"luma_shift":skin_luma_shift},
      "hair_response":{"high_gain":hair_high,"grad_gain":hair_grad,"top_luminance":top_lum,"top_luminance_penalty":top_lum_penalty},
      "central_gate":cg,
      "roi_metrics":metrics,
      "truth_boundary":"FIXED_CAMERA_RELATIVE_OPTIMIZATION_METRICS__NOT_PHOTOREALISM_CERTIFICATION__FINAL_HUMAN_VISUAL_AUDIT_REQUIRED"
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
