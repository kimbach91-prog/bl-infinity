# DEUS V6 Signed Webhook Transport V1

HMAC-SHA256 webhook transport for synthetic and production platform events.

Contract:
- HTTPS only;
- exact raw-body signing;
- timestamp tolerance;
- event and delivery IDs;
- optional replay store;
- no signing secret in receipts;
- sender returns hashes/status, not secret material.

The CI live canary uses synthetic data and a public echo service only to prove outbound HTTPS transport + signature/header/body readback. It does not prove a third-party consumer enforces the signature. Production consumers must call verifySignedWebhook (or an equivalent implementation) before accepting effects.
