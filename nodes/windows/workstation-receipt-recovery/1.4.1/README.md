# DEUS 1T Workstation Receipt Recovery 1.4.1

Purpose: recover the already-completed DEUS V5 Workstation 1.4.0 1T benchmark after the historical receipt-submit HTTP 404, **without rerunning the physical/logical benchmark**.

Server fix:
- runtime commit: `deef0ef53513b353c43d8585eee7f9565fcab0f3`
- endpoint: `POST /workstations/report`
- readback: `GET /workstations/latest`
- promotion gate: exact `receiptDigest` equality and matching `workstationId`.

## Run

Download both files in this folder into the same directory, then double-click:

`RECOVER_1T_RECEIPT_AND_SHOW_RESULTS.bat`

The recovery searches only:
- its own/current package folders;
- DEUS workstation folders directly under the current user's Downloads;
- scoped DEUSNode config/state/secrets locations under ProgramData.

It does not print a token and does not scan unrelated user storage.

Expected local input:
- an existing `benchmark-1t-latest.json` produced by Workstation 1.4.0;
- the existing scoped runtime token available through a DEUS runtime-token environment variable or DEUS package/config/state/secrets reference.

Expected output:
- HTTP 201 accepted;
- runtime readback of `workstation.report`;
- exact local/remote `receiptDigest` match;
- `benchmark-1t-recovery-receipt-1.4.1.json` beside the original benchmark report.

Truth boundary:
`LOCAL_BENCH_COMPLETE != REMOTE_RECEIPT_VERIFIED`
and
`1T_LOGICAL_NAMESPACE != 1T_PHYSICAL_WORKERS`.

Do not place or paste credentials into chat.
