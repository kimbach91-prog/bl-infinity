"""Source-shaped representation adapter between Tycho's structured tool protocol
and KHUB's offline text-only Qwen oracle seam.

Truth scope:
- CPU-testable representation bridge only.
- Does NOT prove Qwen3-VL follows the prompt on GPU.
- Does NOT prove Kaggle offline execution, hidden score, or owner score.

The bridge deliberately avoids pretending KHUB's minimal serve_vlm.py supports
OpenAI tool_calls. Instead it serializes tools/results into a compact text
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


def _matches_json_type(value: Any, expected: str) -> bool:
    """Match the JSON types used by Tycho tool schemas without bool/int leakage."""
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return type(value) is int
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return type(value) is bool
    if expected == "null":
        return value is None
    raise ValueError(f"unsupported schema type: {expected!r}")


def _validate_schema_subset(value: Any, schema: dict, path: str = "$") -> None:
    """Fail closed on the JSON-schema constraints used by Tycho action tools.

    This is intentionally a small validator, not a claim to implement all of
    JSON Schema. It enforces the structural constraints required to prevent a
    syntactically valid text block from being promoted into a semantically
    malformed environment action.
    """
    if not schema:
        return
    if not isinstance(schema, dict):
        raise ValueError(f"{path}: tool schema must be an object")

    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not types or not all(isinstance(t, str) for t in types):
            raise ValueError(f"{path}: invalid schema type declaration")
        if not any(_matches_json_type(value, t) for t in types):
            raise ValueError(f"{path}: expected type {types!r}")

    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list):
            raise ValueError(f"{path}: enum must be an array")
        if value not in enum:
            raise ValueError(f"{path}: value is outside enum")

    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        if not isinstance(properties, dict):
            raise ValueError(f"{path}: properties must be an object")
        if not isinstance(required, list) or not all(isinstance(k, str) for k in required):
            raise ValueError(f"{path}: required must be an array of strings")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"{path}: missing required fields {missing!r}")
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ValueError(f"{path}: additional fields are not allowed: {extras!r}")
        for key, child in value.items():
            if key in properties:
                _validate_schema_subset(child, properties[key], f"{path}.{key}")

    if isinstance(value, list) and "items" in schema:
        items = schema["items"]
        if not isinstance(items, dict):
            raise ValueError(f"{path}: items must be a schema object")
        for index, child in enumerate(value):
            _validate_schema_subset(child, items, f"{path}[{index}]")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise ValueError(f"{path}: string shorter than minLength")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            raise ValueError(f"{path}: string longer than maxLength")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: number below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}: number above maximum")


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

    Rejects unknown tools, malformed JSON, non-object arguments, multiple
    calls, and arguments that violate the selected tool's schema. Fail-closed
    behavior prevents arbitrary or semantically malformed text from being
    promoted to an environment action.
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
    selected = next((tool for tool in tools if tool["name"] == name), None)
    if selected is None:
        raise ValueError(f"unknown tool: {name!r}")
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be an object")
    _validate_schema_subset(arguments, selected.get("schema") or {}, "$.arguments")
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
