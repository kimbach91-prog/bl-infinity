# Public atlas DAG CI

This bounded CI job validates the project's source-linked resource atlas with Dask 2026.8.0. Four partitions run on two single-thread subprocess workers; reduction is compared with a serial oracle, worker use checked, and the scheduler/workers closed.

Input is fifteen CC0 Wikidata metadata records. Repository URLs are data and are never contacted. Top-level Dask/distributed wheels are pinned to PyPI hashes; resolved dependencies are recorded. Owner-private sources, credentials and canonical Drive contents are not published.

GitHub-hosted public project CI admission applies to one job. Runner descriptors and worker PIDs prove that execution window only. No persistent VPS, external worker network, general compute service, performance speedup or AGI is established. No schedule or public server is installed.

Local metadata tests do not import or run Dask; distributed execution requires this repo's GitHub-hosted CI.
