"""Source-shaped representation adapter between Tycho's structured tool protocol
and KHUB's offline text-only Qwen oracle seam.

Truth scope:
- CPU-testable representation bridge only.
- Does NOT prove Qwen3-VL follows the prompt on GPU.
- Does NOT prove Kaggle offline execution, hidden score, or owner score.

The bridge deliberately avoids pretending KHUB's minimal serve_vlm.py supports
OpenAI tool_calls.  Instead it serializes tools/results into a compact text
contract and parses strict model text back into Tycho-shaped tool calls.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_TOOL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def render_tool_contract(tools: list[dict]) -> str:
    """Render Tycho tool specs as a deterministic text contract.

    This is a representation change, not a claim of native function calling.
    """
    specs = []
    for tool in tools:
        specs.append(
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("schema") or {},
            }
        )
    lines = "\n".join(_canonical(spec) for spec in specs)
    return (
        "# Tools\n"
        "You may call one tool at a time. Available tools are JSON specs inside "
        "<tools> tags.\n<tools>\n"
        + lines
        + "\n</tools>\n"
        "When a tool is needed, output exactly one block and no prose:\n"
        "<tool_call>\n"
        '{"name":"<tool-name>","arguments":{}}\n'
        "</tool_call>\n"
        "If no tool is needed, answer with plain text and do not emit a tool_call block."
    )


def render_tool_results(results: list[dict]) -> str:
    """Serialize Tycho tool results for a text-only model turn."""
    payload = []
    for result in results:
        payload.append(
            {
                "id": result.get("id", ""),
                "output": str(result.get("output", "")),
                "has_image": result.get("image_png") is not None,
            }
        )
    return "<tool_response>\n" + _canonical(payload) + "\n</tool_response>"


def parse_tool_calls(text: str, tools: list[dict]) -> list[dict]:
    """Parse strict text calls into Tycho-shaped calls.

    Rejects unknown tools, malformed JSON, non-object arguments, and multiple
    calls.  Fail-closed behavior prevents arbitrary text from being promoted to
    an environment action.
    """
    matches = _TOOL_RE.findall(text or "")
    if not matches:
        return []
    if len(matches) != 1:
        raise ValueError("expected at most one tool_call block")
    try:
        raw = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed tool_call JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("tool_call must be an object")
    name = raw.get("name")
    arguments = raw.get("arguments", {})
    allowed = {tool["name"] for tool in tools}
    if name not in allowed:
        raise ValueError(f"unknown tool: {name!r}")
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be an object")
    digest = hashlib.sha256((name + "\0" + _canonical(arguments)).encode()).hexdigest()[:16]
    return [{"id": f"localcall-{digest}", "name": name, "input": arguments}]


def bridge_response(text: str, tools: list[dict]) -> dict:
    """Return the minimal Tycho transport result shape."""
    calls = parse_tool_calls(text, tools)
    return {
        "text": "" if calls else (text or ""),
        "tool_calls": calls,
        "stop": "tool_call" if calls else "stop",
        "reasoning": "",
        "raw_reasoning": None,
        "usage": {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0},
    }
