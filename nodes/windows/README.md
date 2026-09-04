# DEUS Windows Physical Node — R1

Status: `NON-CANONICAL / OWNER-DEVICE / STAGED-LOCAL-FIRST`

This package converts an owner-authorized Windows workstation into a hardened BL Compute Federation physical node without exposing the DEUS core or opening an Internet-facing worker by default.

## Security invariants

```text
reachable != authorized
heartbeat != authority
worker != control-plane admin
physical ownership != permission escalation
localhost readiness != remote routability
```

The node never receives `BL_CONTROL_TOKEN`. It receives only node-scoped execution and heartbeat credentials. The reference worker retains the BL-CF capability allowlist and intentionally has no generic shell, eval, arbitrary file read or arbitrary URL fetch capability.

Default network posture is **egress-first / localhost-only**:

- worker binds `127.0.0.1:8790`;
- Windows Firewall is enabled on Domain/Private/Public profiles;
- default inbound traffic is blocked;
- no public inbound rule for the worker is created;
- remote routing remains `NOT_AUTHORIZED` until a separate private HTTPS/mTLS/VPN/tunnel transport is explicitly granted and tested.

## What the bootstrap changes

The bootstrap is intentionally conservative and reversible. It:

1. snapshots relevant pre-change security state;
2. creates `%ProgramData%\DEUSNode` with restricted ACLs;
3. generates a stable random node ID and separate execution/heartbeat secrets;
4. protects secrets with Windows DPAPI LocalMachine scope and never prints them;
5. enables Windows Firewall and default inbound blocking;
6. enables firewall dropped-packet logging;
7. attempts to enforce Microsoft Defender real-time, behavior, script and downloaded-file scanning plus PUA/network protection where supported;
8. puts Controlled Folder Access in **AuditMode**, not blocking mode;
9. disables the Remote Registry service;
10. enables PowerShell Script Block Logging policy;
11. disables AutoRun/AutoPlay policy for removable media;
12. installs a pinned BL-CF runtime snapshot locally if Git + Node.js are available (or `-InstallDependencies` is used);
13. registers a startup Scheduled Task running as `SYSTEM` that launches the worker on localhost only;
14. creates a local evidence report and provider-manifest candidate with no secret values.

It does **not** silently disable RDP/WinRM, enable BitLocker, change Secure Boot/TPM state, expose a network port, install a public tunnel, or register itself with a remote coordinator. Those are separate high-impact/authority gates.

## Run on the owner machine

Open **PowerShell as Administrator** and run the checked-out script:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\nodes\windows\bootstrap.ps1 -InstallDependencies
```

Audit only:

```powershell
.\nodes\windows\audit.ps1
```

Rollback baseline changes and stop the node:

```powershell
.\nodes\windows\rollback.ps1
```

Use `rollback.ps1 -PurgeNodeData` only when you intentionally want to remove local node secrets and evidence after rollback.

## Node lifecycle

```text
OWNER CONSENT
  -> LOCAL HARDENING
  -> STAGED_LOCAL_ONLY
  -> LOCAL WORKER HEALTH PASS
  -> PROVIDER GRANT CANDIDATE
  -> SECURE TRANSPORT BINDING
  -> SIGNED/REVOCABLE PROVIDER GRANT
  -> FIRST AUTHENTICATED HEARTBEAT
  -> ROUTABLE PHYSICAL NODE
```

A local worker health check is not evidence that the node is remotely routable. A remote provider becomes active only after BL-CF authority, transport and liveness gates pass.

## Evidence directory

Local runtime evidence is written under:

```text
%ProgramData%\DEUSNode\evidence
```

The report intentionally excludes motherboard/device serial numbers, Windows product keys, credentials and DEUS private-core material.
