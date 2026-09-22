#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import numpy as np
from gnm.shape import gnm_landmarks, gnm_numpy, semantic_sampler

TARGET={
    "jaw_taper":0.64,
    "eye_width":0.185,
    "eye_spacing":0.365,
    "nose_width":0.185,
    "mouth_width":0.335,
    "face_height":0.98,
}
WEIGHT={
    "jaw_taper":2.2,
    "eye_width":1.6,
    "eye_spacing":1.2,
    "nose_width":1.0,
    "mouth_width":1.0,
    "face_height":1.6,
}

def dist(a,b):
    return float(np.linalg.norm(np.asarray(a)-np.asarray(b)))

def metrics(lm):
    face_w=max(1e-8,dist(lm[0],lm[16]))
    left_eye=dist(lm[36],lm[39])/face_w
    right_eye=dist(lm[42],lm[45])/face_w
    eye_l=(lm[36:42].mean(axis=0))
    eye_r=(lm[42:48].mean(axis=0))
    brow=(lm[17:27].mean(axis=0))
    chin=lm[8]
    return {
        "jaw_taper":dist(lm[4],lm[12])/face_w,
        "eye_width":0.5*(left_eye+right_eye),
        "eye_spacing":dist(eye_l,eye_r)/face_w,
        "nose_width":dist(lm[31],lm[35])/face_w,
        "mouth_width":dist(lm[48],lm[54])/face_w,
        "face_height":dist(brow,chin)/face_w,
    }

def score(m):
    return sum(WEIGHT[k]*((m[k]-TARGET[k])/max(0.03,TARGET[k]))**2 for k in TARGET)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start-seed",type=int,default=20263000)
    ap.add_argument("--count",type=int,default=48)
    ap.add_argument("--out",default="runtime/s1_identity_selection.json")
    args=ap.parse_args()
    gnm=gnm_numpy.GNM.from_local(version=gnm_numpy.GNMMajorVersion.V3,variant=gnm_numpy.GNMVariant.HEAD)
    cfg=gnm_landmarks.load_landmarks(gnm_landmarks.GNMLandmarksType.HEAD_SPARSE_68)
    sampler=semantic_sampler.IdentitySampler()
    rows=[]
    for seed in range(args.start_seed,args.start_seed+args.count):
        rng=np.random.default_rng(seed)
        ident=sampler.sample_identity(
            semantic_sampler.Gender.FEMALE,
            semantic_sampler.Ethnicity.ASIAN,
            num_samples=1,rng=rng,verbose=False
        )[0].astype(np.float32)
        ident=np.clip(ident,-2.75,2.75).astype(np.float32)
        expr=np.zeros(gnm.expression_dim,dtype=np.float32)
        rot=np.zeros((gnm.num_joints,3),dtype=np.float32)
        tr=np.zeros(3,dtype=np.float32)
        v=np.asarray(gnm(ident,expr,rot,tr),dtype=np.float64)
        if v.ndim==3: v=v[0]
        lm=(v[cfg.indices]*cfg.weights[...,None]).sum(axis=1)
        m=metrics(lm)
        rows.append({"seed":seed,"score":score(m),"metrics":m})
    rows.sort(key=lambda x:x["score"])
    result={
        "schema":"dige-s1-prototype-identity-selection/1",
        "target":TARGET,
        "weights":WEIGHT,
        "searched":[args.start_seed,args.start_seed+args.count-1],
        "selected":rows[0],
        "top5":rows[:5],
        "truth_boundary":"LANDMARK_RATIO_HEURISTIC_FROM_OWNER_PROTOTYPE__NOT_PIXEL_IDENTITY_MATCH__NO_REFERENCE_PIXELS_USED"
    }
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    env=os.environ.get("GITHUB_ENV")
    if env:
        with open(env,"a",encoding="utf-8") as f:
            f.write(f"DIGE_S1_IDENTITY_SEED={rows[0]['seed']}\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
