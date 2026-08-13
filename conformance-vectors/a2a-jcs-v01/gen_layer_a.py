#!/usr/bin/env python3
"""Generate Layer-A (canonicalization) conformance vectors for the A2A §8.4.1
signature corpus.

Every MUST-ACCEPT vector's expected bytes are computed by running the input
through BOTH independent RFC 8785 oracles (rfc8785.py via PyPI, gowebpki/jcs
via the jcsoracle Go binary) and asserting byte-for-byte agreement -- never
hand-written or guessed. A vector whose oracles disagree is a hard error,
not a vector.

Every MUST-REJECT vector is checked against at least one oracle actually
refusing the input (not asserted by description alone).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import rfc8785

HERE = Path(__file__).resolve().parent
GO_ORACLE = HERE / "oracle-go" / "jcsoracle"
OUT_ROOT = HERE

SPEC_REF_BASE = (
    "https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements"
)


class OracleDisagreement(Exception):
    pass


def py_canonical(obj) -> bytes:
    return rfc8785.dumps(obj)


def go_canonical(raw_json: bytes) -> bytes:
    p = subprocess.run(
        [str(GO_ORACLE)], input=raw_json, capture_output=True, check=False
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"go oracle rejected input it should accept: {p.stderr.decode()}"
        )
    return p.stdout


def go_rejects(raw_json: bytes) -> bool:
    p = subprocess.run(
        [str(GO_ORACLE)], input=raw_json, capture_output=True, check=False
    )
    return p.returncode != 0


def py_rejects(raw_json_text: str) -> bool:
    """True if the Python oracle path cannot produce valid RFC 8785 output.

    Two distinct failure points count: json.loads itself refuses malformed
    JSON (e.g. a lone surrogate that Python's json module happens to accept
    as a string but that cannot round-trip through valid UTF-8), or
    rfc8785.dumps refuses non-JSON values (NaN/Infinity) when asked not to
    silently emit them.
    """
    try:
        obj = json.loads(raw_json_text)
    except (json.JSONDecodeError, ValueError):
        return True
    try:
        out = rfc8785.dumps(obj)
    except (ValueError, TypeError):
        return True
    try:
        out.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return True
    return False


def make_accept(
    vid: str,
    group_dir: str,
    clause: str,
    rationale: str,
    input_obj,
    *,
    raw_override: bytes | None = None,
):
    """Build one MUST-ACCEPT vector, cross-checking both oracles for real."""
    raw = (
        raw_override
        if raw_override is not None
        else json.dumps(input_obj, ensure_ascii=False).encode("utf-8")
    )
    py_out = py_canonical(json.loads(raw.decode("utf-8")))
    go_out = go_canonical(raw)
    if py_out != go_out:
        raise OracleDisagreement(
            f"{vid}: oracles disagree\n  py: {py_out!r}\n  go: {go_out!r}"
        )
    vector = {
        "id": vid,
        "clause": clause,
        "spec_ref": SPEC_REF_BASE,
        "layer": "canonicalization",
        "disposition": "MUST-ACCEPT",
        "rationale": rationale,
        "input": input_obj,
        "expected": {"canonical_utf8_hex": py_out.hex()},
    }
    _write(group_dir, vid, vector)
    return py_out


def make_reject(
    vid: str,
    group_dir: str,
    clause: str,
    rejecting_clause: str,
    rejection_layer: str,
    rationale: str,
    raw_text: str,
):
    """Build one MUST-REJECT vector. Requires BOTH independent oracles to
    refuse the input -- a reject vector adjudicated by only one oracle is
    not adjudicated at all, it is one implementation's opinion wearing a
    two-oracle corpus's credibility. (Discovered the hard way: two earlier
    surrogate-pair vectors passed on Python-only agreement while Go's
    gowebpki/jcs silently substituted U+FFFD instead of erroring -- a real
    oracle disagreement, not a harness bug, and exactly what an OR check
    would hide.)"""
    refused_by_go = go_rejects(raw_text.encode("utf-8"))
    refused_by_py = py_rejects(raw_text)
    if not (refused_by_go and refused_by_py):
        raise RuntimeError(
            f"{vid}: oracles disagree on rejection (go={refused_by_go}, py={refused_by_py}) "
            "-- not a valid two-oracle-adjudicated reject vector"
        )
    vector = {
        "id": vid,
        "clause": clause,
        "spec_ref": SPEC_REF_BASE,
        "layer": "canonicalization",
        "disposition": "MUST-REJECT",
        "rejecting_clause": rejecting_clause,
        "rejection_layer": rejection_layer,
        "rationale": rationale
        + " (confirmed refused by both independent oracles: go+py)",
        "input_raw": raw_text,
    }
    _write(group_dir, vid, vector)


def _write(group_dir: str, vid: str, vector: dict):
    d = OUT_ROOT / group_dir
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{vid}.json"
    p.write_text(
        json.dumps(vector, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {p.relative_to(HERE)}")


def main():
    if not GO_ORACLE.exists():
        print(f"FATAL: go oracle not built at {GO_ORACLE}", file=sys.stderr)
        return 2
    import importlib

    all_groups = ["group_a2", "group_a3", "group_a4", "group_a5", "group_a6"]
    for group_module in sys.argv[1:] or all_groups:
        mod = importlib.import_module(group_module)
        mod.generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
