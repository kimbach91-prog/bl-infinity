# Interface status

As of 2026-08-31:

- `kernel.py`: model-independent pre-LLM cognitive plan builder.
- `engine.py`: kernel-first orchestration; LLM backend optional.
- `github_console.py`: renders kernel-only responses for GitHub Issue commands.
- `.github/workflows/deus-console.yml` on `main`: owner-gated `/deus` issue-comment trigger that checks out `proto/deus-engine-v1`, runs the kernel, and posts a structured response back to the issue.

This is sufficient for structured owner↔kernel interaction through GitHub today. It is not yet sufficient for full natural-language DEUS conversation without attaching a reachable inference backend and durable private state.
