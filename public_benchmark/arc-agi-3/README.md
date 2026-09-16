# ARC-AGI-3 — `ls20` public-development run

## Scope

This run uses the official ARC-AGI Toolkit against the public `ls20` environment. The route was found by black-box state search over observations and actions. The solver did **not** read the game source or hidden state.

This is a **public-development-game** result. It demonstrates an executable planning harness and creates an ARC scorecard/replay; it does not establish performance on unseen competition environments.

## Reproduce

Requirements:

- Python 3.12+
- `arc-agi==0.9.9`
- Internet access to the ARC server
- `ARC_API_KEY` is optional for the public game; without it, the official toolkit requests an anonymous key

Run:

```bash
python replay_route.py --output result.json
```

The script creates a custom scorecard with the public source URL and tags it with `bach-lam-x-deus`, replays the route, closes the scorecard, and writes the returned receipt.

## Current route

- Environment: `ls20-9607627b`
- Levels completed locally: `2 / 7`
- Actions: `58`
- Human baselines for the first two levels: `22`, `123`
- Route discovery: observation-only black-box search, then single-pass replay

The route and its integrity hash are in [`route.json`](./route.json).

## Verified public result

- Official ARC score: **10.714285714285714%**
- Levels: **2 / 7**
- Actions: **58**
- Level 1 efficiency score: **115%** (13 actions; human baseline 22)
- Level 2 efficiency score: **115%** (45 actions; human baseline 123)
- Scorecard: [48180853-70f8-42d8-abe7-b5e00e701650](https://arcprize.org/scorecards/48180853-70f8-42d8-abe7-b5e00e701650)
- Replay: [3e93f549-89f6-4c93-86ad-d9227d5ebd95](https://arcprize.org/replay/3e93f549-89f6-4c93-86ad-d9227d5ebd95)
- Server receipt: [`result.json`](./result.json)

## Honest interpretation

The first two public levels are a progress receipt, not a finished benchmark claim. ARC-AGI-3's official score also rewards action efficiency, and full-game/competition results require all applicable environments under the official rules.
