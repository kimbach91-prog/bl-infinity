#!/usr/bin/env python3
"""Public, zero-network, zero-dependency inference adapter contract canary.

Does NOT run or install model engines. Fail closed for unadmitted native backends.
"""
import json
import time
import unittest
from dataclasses import dataclass

SUPPORTED = {"llama.cpp", "vllm", "ollama", "sglang", "deepinfer", "llama-swap"}
PROTOCOL_ONLY = {"deepseek-recipe"}

@dataclass(frozen=True)
class Admission:
    backend: str
    version_pin: str
    host_ack: bool
    resource_lease: bool
    private_data_grant: bool
    tested_host: str = ""

def evaluate(a: Admission, task_class: str = "S0_PUBLIC") -> dict:
    started = time.perf_counter_ns()
    reasons = []
    if a.backend not in SUPPORTED and a.backend not in PROTOCOL_ONLY:
        reasons.append("UNKNOWN_BACKEND")
    if a.backend in PROTOCOL_ONLY:
        reasons.append("PROTOCOL_ONLY_NOT_INFERENCE")
    if not a.version_pin:
        reasons.append("MISSING_SOURCE_PIN")
    if not a.host_ack or not a.tested_host:
        reasons.append("MISSING_ATTRIBUTABLE_HOST_ACK")
    if not a.resource_lease:
        reasons.append("MISSING_RESOURCE_LEASE")
    if task_class != "S0_PUBLIC" and not a.private_data_grant:
        reasons.append("MISSING_DATA_AUTHORIZATION")
    return {"backend": a.backend, "admitted": not reasons,
            "reasons": reasons, "check_ns": time.perf_counter_ns() - started}

class ContractTests(unittest.TestCase):
    def test_missing_ack_rejected_for_every_engine(self):
        for name in SUPPORTED:
            with self.subTest(name=name):
                r = evaluate(Admission(name, "pinned", False, True, True, "host"))
                self.assertFalse(r["admitted"])
                self.assertIn("MISSING_ATTRIBUTABLE_HOST_ACK", r["reasons"])

    def test_missing_lease_rejected(self):
        self.assertFalse(evaluate(Admission("llama.cpp", "pinned", True, False, True, "host"))["admitted"])

    def test_private_without_grant_rejected(self):
        self.assertFalse(evaluate(Admission("vllm", "pinned", True, True, False, "host"), "S2_PRIVATE")["admitted"])

    def test_protocol_not_executable(self):
        self.assertFalse(evaluate(Admission("deepseek-recipe", "pinned", True, True, True, "host"))["admitted"])

    def test_missing_pin_rejected(self):
        self.assertFalse(evaluate(Admission("sglang", "", True, True, True, "host"))["admitted"])

    def test_unknown_backend_rejected(self):
        self.assertFalse(evaluate(Admission("mystery", "pinned", True, True, True, "host"))["admitted"])

    def test_valid_public_contract_admitted_only_as_contract(self):
        self.assertTrue(evaluate(Admission("llama.cpp", "pinned", True, True, False, "host"))["admitted"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
