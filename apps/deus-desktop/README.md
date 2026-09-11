# DEUS Desktop Client v0.1

Status: `CANDIDATE / CORE-FREE THIN CLIENT`

This is a separate native desktop surface for controlled enterprise/government deployments. It must never ship DEUS private core logic or data.

## Security posture

- no public signup or guest mode;
- no embedded DEUS prompts, evolution logic, routing policy, lineage internals, secrets or protected corpora;
- authentication is delegated to an approved enterprise/government identity flow;
- app stores only an opaque session handle using an OS-backed secure store in production;
- all work data comes from the authorized HMI projection API;
- no generic shell/eval/arbitrary-code bridge;
- no direct filesystem crawl capability;
- no direct core endpoint;
- production builds disable developer tools and use an explicit CSP/capability manifest;
- lost/stolen devices must support session revocation and tenant policy enforcement.

The initial code is an isolated shell and intentionally has no live identity or projection endpoint until those adapters are provisioned and independently tested.
