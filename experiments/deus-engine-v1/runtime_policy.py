#!/usr/bin/env python3
"""Runtime policy for GPT-free/local-only DEUS experiments.

This module is deliberately small and auditable. It prevents an explicitly
GPT-free run from silently falling back to public/proprietary endpoints.
"""
from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from urllib.parse import urlparse


BLOCKED_HOST_SUFFIXES = (
    "openai.com",
    "chatgpt.com",
    "oaistatic.com",
    "oaiusercontent.com",
)


@dataclass(frozen=True)
class EndpointDecision:
    allowed: bool
    mode: str
    host: str
    reason: str


def _is_loopback(host: str) -> bool:
    if host in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def classify_endpoint(url: str, *, allow_remote_owner_hosts: tuple[str, ...] = ()) -> EndpointDecision:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return EndpointDecision(False, "REJECT", host, "MISSING_HOST")

    if any(host == suffix or host.endswith("." + suffix) for suffix in BLOCKED_HOST_SUFFIXES):
        return EndpointDecision(False, "REJECT", host, "PROPRIETARY_GPT_ENDPOINT_BLOCKED")

    if _is_loopback(host):
        return EndpointDecision(True, "LOCAL", host, "LOOPBACK_ENDPOINT")

    allow = {x.strip().lower().rstrip(".") for x in allow_remote_owner_hosts if x.strip()}
    if host in allow:
        return EndpointDecision(True, "OWNER_REMOTE", host, "EXPLICIT_OWNER_ALLOWLIST")

    return EndpointDecision(False, "REJECT", host, "NOT_LOCAL_OR_OWNER_ALLOWLISTED")


def require_gpt_free_endpoint(url: str) -> EndpointDecision:
    allow = tuple(
        x.strip()
        for x in os.getenv("DEUS_OWNER_ENDPOINT_ALLOWLIST", "").split(",")
        if x.strip()
    )
    decision = classify_endpoint(url, allow_remote_owner_hosts=allow)
    if not decision.allowed:
        raise RuntimeError(f"GPT_FREE_POLICY_REJECT:{decision.reason}:{decision.host}")
    return decision


if __name__ == "__main__":
    assert classify_endpoint("http://127.0.0.1:8080/v1").allowed
    assert classify_endpoint("http://localhost:11434/v1").allowed
    assert not classify_endpoint("https://api.openai.com/v1").allowed
    assert not classify_endpoint("https://example.com/v1").allowed
    print("GPT-free runtime endpoint policy: OK")
