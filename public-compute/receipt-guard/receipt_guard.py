"""Receipt-first reconciliation and fail-closed local execution claims.

This library neither authenticates providers nor grants permission to execute.
Call it only after the caller has independently established its authority and
source bindings. A local SQLite claim prevents automatic replay; it is not a
multi-host fence or an exactly-once guarantee for external side effects.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

VERSION = "1.0.1"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def wire(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(wire(value).encode("utf-8")).hexdigest()


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 256 or any(ord(c) < 32 for c in value):
        raise ValueError("invalid identifier")
    return value


def sha(value: Any) -> str:
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise ValueError("invalid digest")
    return value


def integer(value: Any, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not integer")
    if isinstance(value, str):
        if re.fullmatch(r"-?(0|[1-9][0-9]*)", value) is None:
            raise ValueError("invalid integer")
        value = int(value)
    if not isinstance(value, int) or value < minimum:
        raise ValueError("invalid integer")
    return value


def boolean(value: Any) -> bool:
    if type(value) is bool:
        return value
    if value in ("TRUE", "FALSE"):
        return value == "TRUE"
    raise ValueError("invalid boolean")


@dataclass(frozen=True)
class Binding:
    job_id: str
    node_id: str
    mode: str
    command_sha256: str

    def normalized(self) -> dict[str, str]:
        return {
            "job_id": identifier(self.job_id),
            "node_id": identifier(self.node_id),
            "mode": identifier(self.mode),
            "command_sha256": sha(self.command_sha256),
        }


@dataclass(frozen=True)
class Decision:
    state: str
    unique_receipts: int
    delivery_rows: int
    fingerprint: str


def reconcile(binding: Binding, receipts: Iterable[Mapping[str, Any]], *, complete: bool) -> Decision:
    """Classify a task-scoped, independently trusted receipt snapshot.

    There is deliberately no ALLOW_EXECUTE decision. Missing/incomplete data
    cannot authorize a retry. Duplicate delivery ignores delivery timestamps,
    but distinct receipt IDs count as distinct execution claims.
    """
    try:
        expected = binding.normalized()
        items = list(receipts)
        if type(complete) is not bool or len(items) > 10000:
            raise ValueError("invalid snapshot")
        if not complete:
            return Decision("HOLD_INCOMPLETE_SOURCE", 0, len(items), digest(expected))
        seen: dict[str, dict[str, Any]] = {}
        for row in items:
            if not isinstance(row, Mapping):
                raise ValueError("invalid row")
            rid = identifier(row["receipt_id"])
            got = {k: row[k] for k in expected}
            if got != expected:
                return Decision("HOLD_BINDING_CONFLICT", len(seen), len(items), digest(expected))
            state = row["state"]
            if state in ("DONE", "SUCCEEDED"):
                state = "SUCCEEDED"
            normalized = {
                **expected,
                "receipt_id": rid,
                "state": identifier(state),
                "exit_code": integer(row["exit_code"], -(2**31)),
                "timed_out": boolean(row["timed_out"]),
                "stdout_sha256": sha(row["stdout_sha256"]),
                "stderr_sha256": sha(row["stderr_sha256"]),
                "stdout_bytes": integer(row["stdout_bytes"]),
                "stderr_bytes": integer(row["stderr_bytes"]),
            }
            if rid in seen and seen[rid] != normalized:
                return Decision("HOLD_RECEIPT_ID_COLLISION", len(seen), len(items), digest(expected))
            seen[rid] = normalized
        fingerprint = digest({"binding": expected, "receipts": [seen[k] for k in sorted(seen)]})
        if not seen:
            state = "HOLD_NO_RECEIPT"
        elif len(seen) > 1:
            state = "HOLD_MULTIPLE_EXECUTIONS"
        elif any(r["state"] != "SUCCEEDED" or r["exit_code"] != 0 or r["timed_out"] for r in seen.values()):
            state = "HOLD_NON_SUCCESS_RECEIPT"
        else:
            state = "DO_NOT_REPLAY_COMPLETED"
        return Decision(state, len(seen), len(items), fingerprint)
    except (ValueError, TypeError, KeyError, OverflowError):
        return Decision("HOLD_INVALID_SOURCE", 0, 0, "")


class ClaimConflict(RuntimeError):
    pass


class ClaimJournal:
    """Single-filesystem durable claim gate for already-authorized actions.

    Claims are never recycled on timeout. A crash after a claim leaves a HOLD
    until external receipt reconciliation, rather than retrying an ambiguous
    effect. All callers must share this database to obtain this guarantee.
    """
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), timeout=10, isolation_level=None)
        try:
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("CREATE TABLE IF NOT EXISTS claims (node TEXT NOT NULL, job TEXT NOT NULL, binding TEXT NOT NULL, request TEXT NOT NULL, nonce TEXT NOT NULL, state TEXT NOT NULL, result TEXT, PRIMARY KEY(node,job))")
        except BaseException:
            # A rejected database must not leave an open handle on Windows.
            # Re-raise unchanged: cleanup is not permission to execute.
            self.db.close()
            raise

    def close(self) -> None:
        self.db.close()

    def claim(self, binding: Binding, request_sha256: str) -> str | None:
        b = binding.normalized()
        request = sha(request_sha256)
        pin = digest(b)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT binding,request FROM claims WHERE node=? AND job=?", (b["node_id"], b["job_id"])).fetchone()
            if old:
                if old != (pin, request):
                    raise ClaimConflict("same identity has different immutable input")
                self.db.execute("COMMIT")
                return None
            nonce = uuid.uuid4().hex
            self.db.execute("INSERT INTO claims VALUES(?,?,?,?,?,'CLAIMED',NULL)", (b["node_id"], b["job_id"], pin, request, nonce))
            self.db.execute("COMMIT")
            return nonce
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def finish(self, binding: Binding, nonce: str, result_sha256: str) -> None:
        b = binding.normalized()
        result = sha(result_sha256)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT binding,nonce,state,result FROM claims WHERE node=? AND job=?", (b["node_id"], b["job_id"])).fetchone()
            if old is None or old[0] != digest(b) or old[1] != nonce:
                raise ClaimConflict("unowned or mismatched claim")
            if old[2] == "COMPLETED":
                if old[3] != result:
                    raise ClaimConflict("completed result conflict")
            elif old[2] == "CLAIMED":
                self.db.execute("UPDATE claims SET state='COMPLETED',result=? WHERE node=? AND job=?", (result, b["node_id"], b["job_id"]))
            else:
                raise ClaimConflict("unknown claim state")
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def state(self, binding: Binding) -> str | None:
        b = binding.normalized()
        row = self.db.execute("SELECT binding,state FROM claims WHERE node=? AND job=?", (b["node_id"], b["job_id"])).fetchone()
        if row is None:
            return None
        if row[0] != digest(b):
            raise ClaimConflict("binding mismatch")
        return row[1]
