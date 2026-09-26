# DEUS V6 Platform Runtime Postgres Adapter V1

Binds the generic Platform Runtime Foundation to durable PostgreSQL without altering the existing federation authority/runtime tables.

Durable relations:
- tenants and organizations;
- principals/roles/scopes;
- usage events and quota accounting;
- billing credits/invoice preview inputs;
- webhook subscriptions, outbox and delivery state;
- SLO samples.

The schema is additive-only. Production promotion still requires:
1. live Neon schema application/readback;
2. two-tenant authorization/quota/idempotency canary;
3. restart persistence;
4. authenticated API adapter;
5. signed webhook delivery;
6. measured SLO history.

Real money settlement and external provider effects remain separate receipt-gated layers.
