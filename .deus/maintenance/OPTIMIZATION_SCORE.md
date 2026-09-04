# DEUS Device Optimization Score v0.1

A maintenance or scheduling proposal is ranked by expected net useful value, not by maximum utilization.

## Core score

NET_VALUE = USEFUL_GAIN - ENERGY_COST - THERMAL_COST - FAILURE_RISK - SWITCHING_COST - OWNER_DISRUPTION

Where possible, each term is estimated from device-local measurements. If a term is unknown and could materially change the decision, mark UNKNOWN and prefer advisory or fail closed.

## Candidate gains

Examples:
- less idle wakeup overhead;
- lower duplicate polling;
- lower queue thrash;
- better batching;
- better cache hit rate;
- lower memory pressure;
- improved workload locality;
- lower tail latency;
- lower error/retry rate;
- avoided thermal throttling.

## Hard vetoes

A proposal is rejected regardless of score when:
- authorization is invalid or expired;
- owner pause/revocation is active;
- data locality is violated;
- action exceeds device actionMode;
- no rollback exists for a nontrivial configuration mutation;
- thermal/battery/storage safety floor is violated;
- the proposal disables security controls;
- the proposal accesses unrelated personal content;
- expected owner disruption exceeds the declared budget.

## Learning loop

For every applied intervention:
1. capture baseline;
2. predict effect and confidence;
3. apply only within allowed mode;
4. measure post-state;
5. compare prediction vs outcome;
6. rollback if viability worsens;
7. create a deidentified Repair Episode;
8. promote a reusable heuristic only after compatibility and repeated evidence checks.

A failed intervention is preserved as a scar, not deleted from history.
