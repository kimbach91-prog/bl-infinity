"""Read-only custody verifier for the immutable PUBLIC R6.1/R6.2 ZIPs.

Requires an independently obtained archive SHA-256. Never imports archived code,
extracts files, repairs a manifest, or certifies native admission or semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

UPSTREAM_SHA256 = "520c8deb919a3f886b56ecd36d2807ade3f437098881595919c7e9fdd5b06861"
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 2000


class CustodyError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CustodyError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_json(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CustodyError("INVALID_JSON") from exc


def safe_name(name):
    p = PurePosixPath(name)
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name
            or "\x00" in name or p.is_absolute() or ".." in p.parts
            or p.as_posix() != name):
        raise CustodyError("UNSAFE_MEMBER")


def inspect_zip(z):
    infos = z.infolist()
    names = [i.filename for i in infos]
    if not infos or len(infos) > MAX_MEMBERS:
        raise CustodyError("MEMBER_COUNT_BOUND")
    if len(names) != len(set(names)):
        raise CustodyError("DUPLICATE_MEMBER")
    if sum(i.file_size for i in infos) > MAX_EXPANDED_BYTES:
        raise CustodyError("EXPANDED_SIZE_BOUND")
    for info in infos:
        safe_name(info.filename)
        if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
            raise CustodyError("UNSUPPORTED_MEMBER_KIND")
    if z.testzip() is not None:
        raise CustodyError("ZIP_CRC")
    return set(names)


def check_map(z, mapping, prefix=""):
    if type(mapping) is not dict or not mapping:
        raise CustodyError("EMPTY_OR_INVALID_FILE_MAP")
    for name, expected in mapping.items():
        safe_name(name)
        if type(expected) is not str or not re.fullmatch("[0-9a-f]{64}", expected):
            raise CustodyError("INVALID_FILE_DIGEST")
        try:
            actual = digest(z.read(prefix + name))
        except KeyError as exc:
            raise CustodyError("MISSING_FILE:" + prefix + name) from exc
        if actual != expected:
            raise CustodyError("FILE_HASH_MISMATCH:" + prefix + name)
    return len(mapping)


def verify_bytes(raw, expected_sha256, expected_source_id):
    if type(expected_sha256) is not str or not re.fullmatch("[0-9a-f]{64}", expected_sha256):
        raise CustodyError("EXTERNAL_PIN_REQUIRED")
    if type(expected_source_id) is not str or not re.fullmatch("[0-9a-f]{64}", expected_source_id):
        raise CustodyError("EXTERNAL_SOURCE_PIN_REQUIRED")
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise CustodyError("ARCHIVE_SIZE_BOUND")
    if digest(raw) != expected_sha256:
        raise CustodyError("ARCHIVE_PIN_MISMATCH")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = inspect_zip(z)
            release = read_json(z.read("RELEASE_MANIFEST.json"))
            if type(release) is not dict or release.get("schema") not in {
                    "deus-one-r61-source-release/1", "deus-one-r62-source-release/1"}:
                raise CustodyError("UNSUPPORTED_RELEASE_SCHEMA")
            files = release.get("files")
            release_count = check_map(z, files)
            if names != set(files) | {"RELEASE_MANIFEST.json"}:
                raise CustodyError("MANIFEST_MEMBER_SET_MISMATCH")
            bindings = read_json(z.read("SOURCE_BINDINGS.json"))
            if type(bindings) is not dict or bindings.get("source_archive_sha256") != UPSTREAM_SHA256:
                raise CustodyError("UPSTREAM_BINDING_MISMATCH")
            source_count = check_map(z, bindings.get("files"))
            source_id = digest(json.dumps(bindings, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=False, allow_nan=False).encode("utf-8"))
            if source_id != expected_source_id:
                raise CustodyError("SOURCE_ID_MISMATCH")
            if (release["schema"] == "deus-one-r62-source-release/1"
                    or "source_id" in release) and source_id != release.get("source_id"):
                raise CustodyError("MANIFEST_SOURCE_ID_MISMATCH")
            previous = read_json(z.read("upstream/r51/SOURCE_SHA256.json"))
            previous_files = previous.get("files", previous) if type(previous) is dict else None
            previous_count = check_map(z, previous_files, "upstream/r51/")
            original = z.read("source/DEUS_CHESS_R51_SOURCE_RECONSTRUCTION_20261017.zip")
            if digest(original) != UPSTREAM_SHA256:
                raise CustodyError("UPSTREAM_ARCHIVE_PIN_MISMATCH")
            with zipfile.ZipFile(io.BytesIO(original)) as upstream:
                inspect_zip(upstream)
            return {"state": "PASS_ARCHIVE_CUSTODY_ONLY", "archive_sha256": expected_sha256,
                    "archive_bytes": len(raw), "members": len(names),
                    "release_files_checked": release_count, "source_files_checked": source_count,
                    "predecessor_entries_checked": previous_count, "source_id": source_id,
                    "archived_code_imported": False, "runtime_suite_executed": False,
                    "native_admission": False, "semantic_correctness_verified": False,
                    "signature_or_identity_authentication": False, "physical_capacity_credit": 0}
    except (KeyError, zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise CustodyError("ARCHIVE_STRUCTURE_OR_READ_ERROR:" + type(exc).__name__) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expect-sha256", required=True)
    parser.add_argument("--expect-source-id", required=True)
    args = parser.parse_args()
    try:
        if args.archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise CustodyError("ARCHIVE_SIZE_BOUND")
        result = verify_bytes(args.archive.read_bytes(), args.expect_sha256, args.expect_source_id)
        result["verifier_sha256"] = digest(Path(__file__).read_bytes())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (CustodyError, OSError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "HOLD", "reason": str(exc), "native_admission": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
