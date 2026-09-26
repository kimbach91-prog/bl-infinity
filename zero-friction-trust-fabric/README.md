# DEUS Zero-Friction Trust Fabric V1

Security is expressed as delegated machine identity, short-lived capabilities, continuous authorization, revocation and receipts — not repeated password prompts.

## Default flow

consent / delegation
-> principal binding
-> federated or refreshable credential
-> short-lived capability
-> continuous risk/policy evaluation
-> machine execution
-> receipt
-> rotate/revoke

User presence is an edge condition, not the default control path.

## Design goals

- standing owner delegation for explicitly managed accounts;
- OIDC/OAuth/workload federation/service identities instead of long-lived static keys where supported;
- risk-adaptive authorization;
- provider/account scopes remain authoritative;
- immediate revocation;
- short-lived non-transferable capability grants;
- provider-required user presence is surfaced as one exact step-up and auto-resume;
- no secret values in chat or canonical Drive state.

This models the security style of modern large platforms: connect once, preserve delegated identity, apply policy continuously, and prompt only when action/provider risk requires it.
