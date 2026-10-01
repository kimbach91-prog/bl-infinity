import hashlib, json, os, platform, time
payload = {
    "schema":"deus-shadow-system-canary/1",
    "task":"fresh_github_actions_compute_canary",
    "runner_os":platform.platform(),
    "python":platform.python_version(),
    "cpu_count":os.cpu_count(),
    "ts_unix":int(time.time()),
    "input_contract":"S0_PUBLIC_DETERMINISTIC",
}
blob=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
payload["receipt_sha256"]=hashlib.sha256(blob).hexdigest()
payload["passed"]=bool(payload["cpu_count"] and payload["python"])
print(json.dumps(payload,separators=(",",":")))
if not payload["passed"]:
    raise SystemExit(2)
