#!/usr/bin/env python3
import argparse, json, math
from pathlib import Path
from PIL import Image


def load_rgb(path):
    return Image.open(path).convert("RGB")


def region_metrics(rgb):
    w, h = rgb.size
    if (w, h) != (900, 900):
        raise SystemExit(f"UNEXPECTED_IMAGE_SIZE {w}x{h}")

    pixels = list(rgb.getdata())
    lum = [0.2126*r + 0.7152*g + 0.0722*b for r, g, b in pixels]

    central_count = central_dark = 0
    central_lum_sum = central_edge_sum = 0.0
    top_count = top_dark = 0
    left_count = left_dark = 0
    right_count = right_dark = 0

    for y in range(h):
        row = y * w
        for x in range(w):
            idx = row + x
            value = lum[idx]
            is_dark = value < 70.0

            if 235 < y < 375 and 315 < x < 585:
                top_count += 1
                top_dark += int(is_dark)
            if 300 < y < 520 and 280 < x < 360:
                left_count += 1
                left_dark += int(is_dark)
            if 300 < y < 520 and 540 < x < 620:
                right_count += 1
                right_dark += int(is_dark)

            in_face = ((x - 450) / 145.0) ** 2 + ((y - 485) / 205.0) ** 2 <= 1.0
            if in_face and 340 < y < 610 and 335 < x < 565:
                central_count += 1
                central_dark += int(is_dark)
                central_lum_sum += value
                gx = 0.0 if x == 0 else abs(value - lum[idx - 1])
                gy = 0.0 if y == 0 else abs(value - lum[idx - w])
                central_edge_sum += math.hypot(gx, gy)

    return {
        "central_dark_fraction": central_dark / central_count,
        "central_mean_luminance": central_lum_sum / central_count,
        "central_edge_mean": central_edge_sum / central_count,
        "top_center_dark_fraction": top_dark / top_count,
        "left_side_dark_fraction": left_dark / left_count,
        "right_side_dark_fraction": right_dark / right_count,
    }


def score(m):
    symmetry = abs(m["left_side_dark_fraction"] - m["right_side_dark_fraction"])
    central = m["central_dark_fraction"]
    lum = m["central_mean_luminance"]
    top = m["top_center_dark_fraction"]
    hard = central <= 0.12 and lum >= 115.0 and symmetry <= 0.22
    s = 100.0
    s -= 160.0 * central
    s -= 45.0 * symmetry
    s -= 20.0 * abs(top - 0.48)
    if lum < 135.0:
        s -= 0.25 * (135.0 - lum)
    return hard, max(-100.0, min(100.0, s)), symmetry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--candidate-id", required=True)
    ap.add_argument("--guide-dist", required=True, type=float)
    args = ap.parse_args()
    m = region_metrics(load_rgb(args.image))
    hard, s, sym = score(m)
    out = {
        "schema": "DIGE_C33_VISUAL_METRICS_V1",
        "candidate_id": args.candidate_id,
        "guide_dist_m": args.guide_dist,
        "image": Path(args.image).name,
        "hard_gate_pass": hard,
        "score": s,
        "side_symmetry_delta": sym,
        "metrics": m,
        "hard_gate": {
            "central_dark_fraction_max": 0.12,
            "central_mean_luminance_min": 115.0,
            "side_symmetry_delta_max": 0.22,
        },
        "truth_boundary": "FIXED_CAMERA_HEURISTIC_PRESELECTOR__HUMAN_FINAL_AUDIT_STILL_REQUIRED",
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
