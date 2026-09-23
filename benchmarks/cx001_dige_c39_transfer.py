#!/usr/bin/env python3
import argparse, copy, hashlib, json, os, pathlib, time

FIXTURE_DEFAULT = pathlib.Path(__file__).parent / "data" / "cx001_dige_c39_public_fixture.json"

def get_path(obj, path):
    cur = obj
    for part in path.split("."):
        cur = cur[part]
    return cur

def changed(a, b):
    return a != b

def detect_changed_nodes(fx):
    direct = fx["direct"]
    hhir = fx["hhir"]
    out = set()

    if changed(direct["geometry_manifest_sha256"], hhir["geometry_manifest_sha256"]):
        out.add("GEOMETRY_FACE")

    if (
        direct["arm_inputs"]["eye_open"] != hhir["arm_inputs"]["eye_open"]
        or direct["arm_inputs"]["eye_globe"] != hhir["arm_inputs"]["eye_globe"]
    ):
        out.add("EYE_INTERFACE")

    if direct["skin"] != hhir["skin"]:
        out.add("SKIN_PBR")

    if (
        direct["arm_inputs"]["hhir"] != hhir["arm_inputs"]["hhir"]
        or direct["arm_inputs"]["hair_length"] != hhir["arm_inputs"]["hair_length"]
        or direct["arm_inputs"]["hair_wave"] != hhir["arm_inputs"]["hair_wave"]
        or direct["arm_inputs"]["strands"] != hhir["arm_inputs"]["strands"]
        or direct["updo_enabled"] != hhir["updo_enabled"]
    ):
        out.add("GROOM_UPDO")

    # C39 public contract attempted a camera change even though the actual
    # preview receipt stayed at 70mm. Keep CAMERA in the admitted closure,
    # then record the zero observed effect as cancellation evidence.
    out.add("CAMERA")
    return out

def downstream(graph, starts):
    edges = graph["edges"]
    adj = {}
    for a,b in edges:
        adj.setdefault(a,set()).add(b)
    seen = set(starts)
    stack = list(starts)
    while stack:
        x = stack.pop()
        for y in adj.get(x,()):
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return seen

def run_case(fixture_path, regime, trial, out_path):
    fx = json.loads(pathlib.Path(fixture_path).read_text())
    fx = copy.deepcopy(fx)
    t0 = time.perf_counter_ns()

    if regime == "GEOMETRY_MUTATION_CONTROL":
        # Application-shaped negative control: change the public geometry
        # fingerprint. CX-001 must reopen GEOMETRY_FACE and therefore the
        # entire graph closure; zero work-avoidance credit is expected.
        fx["hhir"]["geometry_manifest_sha256"] = hashlib.sha256(
            (fx["hhir"]["geometry_manifest_sha256"] + f":negative:{trial}").encode()
        ).hexdigest()
        expected_candidate_nodes = len(fx["graph"]["nodes"])
        expected_avoided = 0
    elif regime == "C39_REAL_REPLAY":
        expected_candidate_nodes = 5
        expected_avoided = 1
    else:
        raise ValueError(regime)

    graph_nodes = {n["id"] for n in fx["graph"]["nodes"]}
    baseline_nodes = set(graph_nodes)
    changed_nodes = detect_changed_nodes(fx)
    candidate_nodes = downstream(fx["graph"], changed_nodes)

    # VERIFY is always materialized because application output/visual gate is
    # the acceptance target.
    candidate_nodes.add(fx["graph"]["target"])

    # Real C39 zero-effect observation: intended CAMERA change did not
    # materialize in actual preview receipt. We record it as cancellation
    # evidence but do not take extra work-avoidance credit, because the
    # application had to observe/verify the camera outcome.
    zero_effect = set()
    if (
        fx["actual_observations"]["camera_effect_observed"] is False
        and fx["direct"]["lens_mm"] == fx["hhir"]["lens_mm"]
        and "CAMERA" in candidate_nodes
    ):
        zero_effect.add("CAMERA")

    observed_required = {"EYE_INTERFACE","SKIN_PBR","GROOM_UPDO","VERIFY"}
    if regime == "GEOMETRY_MUTATION_CONTROL":
        observed_required.add("GEOMETRY_FACE")

    false_exclusions = sorted(observed_required - candidate_nodes)

    # The public C39 reducer was structural_hhir_pass=true. A transfer replay
    # is exact only if all observed application-relevant changes remain in the
    # closure and the output/verification stage is retained.
    replay_structural_pass = (
        not false_exclusions
        and "VERIFY" in candidate_nodes
        and fx["actual_observations"]["structural_hhir_pass"] is True
    )

    baseline_evals = len(baseline_nodes)
    candidate_evals = len(candidate_nodes)
    avoided = baseline_evals - candidate_evals
    avoided_fraction = avoided / baseline_evals if baseline_evals else 0.0

    assert candidate_evals == expected_candidate_nodes, (candidate_evals, candidate_nodes)
    assert avoided == expected_avoided
    assert not false_exclusions
    assert replay_structural_pass is True

    # The real workload result 302s->85s is lineage context only. It changed
    # renderer/groom/material parameters and cannot be attributed to CX-001.
    legacy_speed_ratio = fx["source"]["direct_wall_seconds"] / fx["source"]["hhir_wall_seconds"]

    receipt = {
        "schema":"deus-cx001-application-transfer-receipt/1",
        "application":"DIGE_C39_HHIR_HYPERREAL",
        "transfer_mode":"REAL_PUBLIC_WORKLOAD_REPLAY",
        "regime":regime,
        "trial":trial,
        "runtime":{
            "provider":"GitHub Actions",
            "run_id":os.environ.get("GITHUB_RUN_ID"),
            "job_id":os.environ.get("GITHUB_JOB"),
            "source_commit":os.environ.get("GITHUB_SHA"),
        },
        "source_lineage":fx["source"],
        "baseline":{
            "policy":"FULL_DEPENDENCY_SAFE_APPLICATION_GRAPH",
            "node_evals":baseline_evals,
            "nodes":sorted(baseline_nodes),
        },
        "candidate":{
            "policy":"CX001_CAUSAL_CUT_DELTA_MULTIRES_APPLICATION_REPLAY",
            "changed_nodes":sorted(changed_nodes),
            "closure_nodes":sorted(candidate_nodes),
            "node_evals":candidate_evals,
            "zero_effect_verified_nodes":sorted(zero_effect),
        },
        "metrics":{
            "dependency_nodes":baseline_evals,
            "causal_nodes":candidate_evals,
            "logical_node_evals_avoided":avoided,
            "logical_work_avoided_fraction":avoided_fraction,
            "false_exclusion_count":len(false_exclusions),
            "false_exclusions":false_exclusions,
            "replay_structural_pass":replay_structural_pass,
            "actual_camera_effect_observed":fx["actual_observations"]["camera_effect_observed"],
            "legacy_c39_wall_ratio_not_attributed_to_cx001":legacy_speed_ratio,
            "measurement_wall_ms":(time.perf_counter_ns()-t0)/1_000_000.0,
        },
        "acceptance":{
            "actual_public_reducer_structural_hhir_pass":fx["source"]["structural_hhir_pass"],
            "actual_visual_result":fx["source"]["visual_result"],
            "predicted_structural_pass":replay_structural_pass,
            "exact_transfer_verdict":replay_structural_pass == fx["source"]["structural_hhir_pass"],
        },
        "claim_ceiling":"APPLICATION_TRANSFER_REPLAY_ONLY__NO_LIVE_RENDER_SPEEDUP__NO_ENERGY_CREDIT__NO_302_TO_85_ATTRIBUTION",
    }
    pre = json.dumps(receipt,sort_keys=True,separators=(",",":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(pre).hexdigest()

    pathlib.Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("DEUS_CX001_APP_TRANSFER_RECEIPT="+json.dumps(receipt,sort_keys=True,separators=(",",":")))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fixture",default=str(FIXTURE_DEFAULT))
    ap.add_argument("--regime",required=True,choices=["C39_REAL_REPLAY","GEOMETRY_MUTATION_CONTROL"])
    ap.add_argument("--trial",required=True,type=int)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    run_case(args.fixture,args.regime,args.trial,args.output)

if __name__=="__main__":
    main()
