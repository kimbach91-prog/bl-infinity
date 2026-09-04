TASK_ID: DEUS-INFRA-HARDENING-20260904-003
MODE: INFRA_HARDENING
TARGET: AUX_CLOUD_GITHUB_RUNNER
PRIORITY: P0
ALLOWED_OUTPUT: ACK_AND_DEFENSIVE_AUDIT
CANONICAL_WRITE: DENIED

GOAL:
Verify producer -> cloud receptor -> auxiliary compute -> durable return and run the fixed defensive repository audit.

SUCCESS_CRITERIA:
- CLOUD_RECEPTOR_READ
- CLOUD_COMPUTE_RETURN
- file-only findings, never secret values
- no destructive remediation

NODE_STATUS_POLICY:
Infrastructure ACK does not imply Gemini/Claude/Grok/GPT read or execution. Each independent LLM node remains OFFLINE_OR_UNVERIFIED until its own authenticated worker returns a node-level ACK.