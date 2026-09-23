import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ALLOWED_OPERATORS = {"flow_matching", "diffusion", "autoregressive_latent"}
BANNED_PRIMARY = {
    "affine_transform", "homography", "ken_burns", "optical_flow_warp_only",
    "blender_root_motion_only", "duplicate_frame_interpolation", "crossfade_only",
}

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--receipt", required=True)
    args=p.parse_args()
    video=pathlib.Path(args.video)
    receipt_path=pathlib.Path(args.receipt)
    if not video.is_file() or not receipt_path.is_file():
        raise SystemExit("missing input")
    r=json.loads(receipt_path.read_text())
    reasons=[]
    if r.get("generation_operator") not in ALLOWED_OPERATORS:
        reasons.append("operator_not_generative")
    if int(r.get("temporal_latent_frames",0)) <= 1:
        reasons.append("temporal_extent_not_proven")
    if int(r.get("sampling_steps",0)) <= 0:
        reasons.append("sampling_not_proven")
    if r.get("spatiotemporal_modeling") is not True:
        reasons.append("spatiotemporal_modeling_not_proven")
    if int(r.get("proprietary_video_api_calls",-1)) != 0:
        reasons.append("proprietary_video_api_calls_nonzero_or_unknown")
    primary=set(r.get("primary_motion_operators") or [])
    if primary & BANNED_PRIMARY:
        reasons.append("banned_primary_motion_operator")
    observed_sha=sha256(video)
    if observed_sha != r.get("output_sha256"):
        reasons.append("output_sha256_mismatch")
    probe=subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=codec_name,width,height,r_frame_rate,nb_frames,duration",
         "-of","json",str(video)],capture_output=True,text=True,check=False
    )
    if probe.returncode != 0:
        reasons.append("ffprobe_failed")
        ffprobe={}
    else:
        ffprobe=json.loads(probe.stdout)
    result={
        "schema":"deus-native-generative-video-v2-readback/1",
        "provenance_pass":not reasons,
        "reasons":reasons,
        "video_sha256":observed_sha,
        "receipt_output_sha256":r.get("output_sha256"),
        "ffprobe":ffprobe,
        "truth_boundary":"PROVENANCE_PASS_DOES_NOT_IMPLY_NATURALNESS_PASS",
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(0 if not reasons else 2)

if __name__=="__main__":
    main()
