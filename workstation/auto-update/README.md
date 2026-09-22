# DEUS Workstation Auto-Update

Control path:

`Drive 77_WORKSTATION_UPDATE_CHANNEL -> DEUS Runtime -> Windows daemon -> immutable GitHub release bundle -> self-test -> apply/rollback -> ACK -> Drive`.

The channel is declarative only. It does not expose a remote shell or arbitrary command endpoint.

A release is eligible only when state is `RELEASED`, generation is monotonic, the target node and rollout match, the version is strictly newer, the apply-after gate is satisfied, and self-test + rollback policies are enabled.

`RELEASE_REF` format: `github_raw_bundle|owner/repo|COMMIT_SHA|base/path`.

`ARTIFACT_SHA256` is the SHA-256 of `release-manifest.json` at that immutable commit. The release manifest then pins the SHA-256 of every downloaded source file. The bootstrap rejects path traversal and only accepts the bounded source/text extension allowlist.

Drive is canonical control state, GitHub is code/version state, and workstation/runtime receipts are execution truth.
