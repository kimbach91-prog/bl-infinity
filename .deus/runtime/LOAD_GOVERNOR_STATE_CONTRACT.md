# Load Governor State Contract

State is advisory operational state, not canonical project memory.

Persist only counters/checkpoint metadata needed to resume safely. Do not persist process-local monotonic timestamps across restarts. On restart, reset temporal gates and rebuild pressure state conservatively from fresh provider responses.

The governor must fail toward lower pressure: if state is corrupt or unavailable, start with conservative defaults rather than increasing concurrency.
