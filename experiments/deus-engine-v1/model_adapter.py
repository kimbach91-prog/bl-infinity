#!/usr/bin/env python3
"""DEUS Engine v1 — replaceable inference adapters.

The adapter is an instrument, not the identity-bearing core. The HTTP adapter
speaks the common OpenAI-compatible chat-completions shape so it can be pointed
at local servers such as llama.cpp/vLLM/SGLang/Ollama-compatible gateways or
other explicitly authorized endpoints.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from runtime_policy import require_gpt_free_endpoint


@dataclass(frozen=True)
class Candidate:
    adapter_id: str
    model_id: str
    text: str
    raw_meta: dict


class ModelAdapter(Protocol):
    adapter_id: str
    model_id: str

    def generate(self, prompt: str, *, temperature: float = 0.8,
                 max_tokens: int = 1200) -> Candidate: ...


class MockAdapter:
    adapter_id = "MOCK"
    model_id = "NO_MODEL"

    def generate(self, prompt: str, *, temperature: float = 0.8,
                 max_tokens: int = 1200) -> Candidate:
        return Candidate(self.adapter_id, self.model_id,
                         "[MOCK] " + prompt[: min(len(prompt), 500)],
                         {"temperature": temperature, "max_tokens": max_tokens})


class OpenAICompatHTTPAdapter:
    """Minimal HTTP adapter with no SDK dependency.

    This class is transport-compatible with OpenAI-style APIs but does not imply
    an OpenAI provider. Use `LocalOnlyHTTPAdapter` for GPT-free runs.

    Environment defaults:
      DEUS_LLM_BASE_URL=http://127.0.0.1:8000/v1
      DEUS_LLM_MODEL=<server model id>
      DEUS_LLM_API_KEY=<optional>
    """

    def __init__(self, *, base_url: str | None = None, model_id: str | None = None,
                 api_key: str | None = None, adapter_id: str = "OPENAI_COMPAT"):
        self.base_url = (base_url or os.getenv("DEUS_LLM_BASE_URL") or "http://127.0.0.1:8000/v1").rstrip("/")
        self.model_id = model_id or os.getenv("DEUS_LLM_MODEL") or "local-model"
        self.api_key = api_key if api_key is not None else os.getenv("DEUS_LLM_API_KEY")
        self.adapter_id = adapter_id

    def generate(self, prompt: str, *, temperature: float = 0.8,
                 max_tokens: int = 1200) -> Candidate:
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        meta = {
            "id": data.get("id"),
            "usage": data.get("usage"),
            "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
        }
        return Candidate(self.adapter_id, self.model_id, text, meta)


class LocalOnlyHTTPAdapter(OpenAICompatHTTPAdapter):
    """GPT-free transport gate for owner-controlled/local model servers.

    The protocol may be OpenAI-compatible, but the endpoint itself must pass the
    local/owner allowlist policy. There is no silent provider fallback.
    """

    def __init__(self, *, base_url: str | None = None, model_id: str | None = None,
                 api_key: str | None = None, adapter_id: str = "LOCAL_ONLY"):
        super().__init__(
            base_url=base_url,
            model_id=model_id,
            api_key=api_key,
            adapter_id=adapter_id,
        )
        self.endpoint_decision = require_gpt_free_endpoint(self.base_url)

    def generate(self, prompt: str, *, temperature: float = 0.8,
                 max_tokens: int = 1200) -> Candidate:
        # Recheck on every generation in case runtime configuration changes.
        decision = require_gpt_free_endpoint(self.base_url)
        candidate = super().generate(prompt, temperature=temperature, max_tokens=max_tokens)
        meta = dict(candidate.raw_meta)
        meta.update({
            "runtime_policy": "GPT_FREE",
            "endpoint_mode": decision.mode,
            "endpoint_host": decision.host,
        })
        return Candidate(candidate.adapter_id, candidate.model_id, candidate.text, meta)
