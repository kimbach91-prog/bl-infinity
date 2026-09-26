# DEUS V6 Developer Platform Contract V1

A large platform needs a stable public contract, not only internal APIs.

This module defines the generic developer-facing invariants DEUS should preserve across REST/streaming/SDK surfaces:

- semantic API version registry;
- same-major compatibility rule;
- minimum deprecation notice;
- tenant-scoped idempotency;
- opaque signed cursor pagination;
- monotonic streaming events;
- structured request and error envelopes;
- trace propagation;
- TypeScript, Python and Go SDK manifest;
- retries only for explicitly retryable errors.

This is a contract/runtime primitive, not proof that public packages, a docs portal, public DNS, or 99.9% SLO are already deployed.
