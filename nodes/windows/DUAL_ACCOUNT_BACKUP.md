# DEUS Dual-Account Drive Backup — Windows R1

Status: `OWNER-DEVICE / EXPLICIT-AUTH / COPY-ONLY / NON-CANONICAL`

Purpose: create **independent, versioned snapshots** of important Google Drive material from one owner-authorized rclone remote into a different owner-authorized rclone remote, without mirroring deletions.

## Invariants

```text
BACKUP != MIRROR
SHARED ACCESS != INDEPENDENT COPY
REACHABLE ACCOUNT != AUTHORIZED ACCOUNT
SOURCE DELETE != DESTINATION DELETE
GOOGLE-NATIVE LINK != OFFLINE-INDEPENDENT SNAPSHOT
SUCCESS CLAIM REQUIRES READBACK
```

This package deliberately does not use `rclone sync`, `move`, `delete` or `purge` against either remote.

## Why materialize first

Google Docs, Sheets and Slides are provider-native objects rather than ordinary file bytes. The backup script first copies from the source Drive to local staging and asks rclone to export native objects into standard archival files such as DOCX, XLSX, PPTX, SVG or PDF. It then uploads those materialized files to the second account **without importing them back into Google-native formats**.

This gives the destination account an independent file object that does not depend on the source native document continuing to exist. The trade-off is intentional: an exported Office/PDF snapshot is for preservation and restore, not a perfect clone of every Google-native feature, comment, revision or sharing state.

## Required preparation

1. Install rclone on the owner-controlled Windows machine.
2. Run `rclone config` locally.
3. Create two distinct Google Drive remotes, for example:
   - `kimbach91`
   - `phdmedia`
4. Authenticate each remote interactively to the intended Google account.
5. Verify identity manually before any write:

```powershell
rclone about kimbach91:
rclone about phdmedia:
rclone lsd kimbach91:
rclone lsd phdmedia:
```

Remote aliases are local labels only. The script cannot prove which Google identity an alias represents, so the human owner must verify account identity during rclone authorization.

## Safe dry run

Example for selected critical paths:

```powershell
.\nodes\windows\backup-dual-drive.ps1 `
  -SourceRemote kimbach91 `
  -DestinationRemote phdmedia `
  -SourcePaths @('DEUS','BL∞','THEORY GROUP') `
  -DryRun
```

`ROOT` is an explicit token for the whole source Drive. An empty path is not accepted as an accidental full-drive request.

```powershell
.\nodes\windows\backup-dual-drive.ps1 `
  -SourceRemote kimbach91 `
  -DestinationRemote phdmedia `
  -SourcePaths @('ROOT') `
  -DryRun
```

## Execute a versioned snapshot

After inspecting the dry-run output:

```powershell
.\nodes\windows\backup-dual-drive.ps1 `
  -SourceRemote kimbach91 `
  -DestinationRemote phdmedia `
  -SourcePaths @('DEUS','BL∞','THEORY GROUP')
```

Each execution writes to a timestamped destination tree such as:

```text
phdmedia:DEUS-DUAL-BACKUP/20260904T153500Z/001-DEUS/...
```

A later run creates a new timestamp instead of deleting or mutating an earlier snapshot.

## Verification

For every source path the script:

1. materializes source files into a new local staging directory;
2. computes SHA-256 for every materialized file and writes `__BL_BACKUP_MANIFEST.json`;
3. uploads with `rclone copy --immutable`;
4. runs `rclone check --download --one-way` so the destination content is downloaded and compared with the local staged source;
5. emits an evidence receipt under `%ProgramData%\DEUSNode\evidence`.

A successful receipt state is:

`VERIFIED_MATERIALIZED_SNAPSHOT`

A dry run is only:

`DRY_RUN_ONLY`

## What the receipt proves

A successful receipt proves that the configured source remote was materialized, copied into the configured destination remote, and content-checked for that run.

It does **not** prove:

- that a remote alias belongs to a particular human/account unless authorization identity was independently verified;
- that Google-native revision history/comments/sharing were preserved;
- that an exported DOCX/XLSX/PPTX/PDF is semantically identical to every Google-native feature;
- that future source changes are automatically backed up;
- that restore has been tested.

`BACKUP != RECOVERY UNTIL RESTORE IS TESTED` remains in force.

## Restore drill

Restore should be tested into a **new temporary folder**, never over the active source:

```powershell
rclone copy phdmedia:DEUS-DUAL-BACKUP/<timestamp>/<slot> C:\DEUS-Restore-Test --immutable
```

Then compare the downloaded manifest and SHA-256 hashes locally. Only after a successful restore drill should a snapshot be promoted from `BACKUP_VERIFIED` to `RECOVERY_VERIFIED` in any operational ledger.

## Delete protection

The script intentionally has no remote deletion primitive. If retention cleanup is ever added, it must be a separate command/tool with a separate explicit authorization and must never be inferred from ordinary backup execution.
