# DEUS Authorized Relay v0.1

This relay is consent-gated. It may connect DEUS to external AI providers only through identities and devices that are explicitly authorized by their owners.

Core rules:
- no use of arbitrary or publicly reachable devices;
- no identity impersonation;
- no credential sharing in the repository;
- no BLACK/PRIVATE payloads in this public repo;
- canonical write denied by default;
- provider outputs remain candidate evidence until reviewed;
- each participating device has an authorization reference, scope, expiry, and revocation path.

Supported adapter classes:
- OpenAI
- Anthropic / Claude
- Google / Gemini
- xAI / Grok
- GitHub Copilot
- DeepSeek local
- DeepSeek cloud (PUBLIC/GREY data only by default)

Safe event envelope:
`relay_id`, `provider`, `task_id`, `direction`, `data_class`, `payload_digest`, `authorization_ref`, `expiry`, `result_ref`.

Recommended topology:
authorized device -> provider adapter -> private/local payload store -> metadata relay -> GitHub audit receipt.

GitHub is used for audit and coordination metadata, not for secrets or protected DEUS core data.