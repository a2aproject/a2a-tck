#!/usr/bin/env python3
"""Generate Layer-A (canonicalization) conformance vectors for the A2A signature corpus.

Every MUST-ACCEPT vector's expected bytes are computed by running the input
through BOTH independent RFC 8785 oracles (rfc8785.py via PyPI, gowebpki/jcs
via the jcsoracle Go binary) and asserting byte-for-byte agreement -- never
hand-written or guessed. A vector whose oracles disagree is a hard error,
not a vector.

Every MUST-REJECT vector needs BOTH oracles to refuse the input; one
refusal alone is a hard error, not a vector.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

from pathlib import Path
from typing import Any, Self

import rfc8785


HERE = Path(__file__).resolve().parent
GO_ORACLE = HERE / "oracle-go" / "jcsoracle"
OUT_ROOT = HERE

SPEC_REF_BASE = (
    "https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements"
)

#: The RFC 8259 number grammar, which a JSONNumberToken must match in full.
_JSON_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")


class OracleDisagreementError(Exception):
    """Raised when the two independent RFC 8785 oracles disagree on a MUST-ACCEPT vector."""


class JSONNumberToken(str):
    """A JSON number that a vector file must carry exactly as spelled.

    Python's json module cannot write some number tokens a canonicalizer has
    to handle. The integer ``-0`` parses to the int 0 and is written back as
    ``0``, which would make the vector test a different input. A value wrapped
    in this class is written into the vector file, and into the bytes the Go
    oracle reads, as this exact token.
    """

    def __new__(cls, token: str) -> Self:
        """Accept only a complete RFC 8259 number token."""
        if not _JSON_NUMBER.fullmatch(token):
            raise ValueError(f"{token!r} is not an RFC 8259 number token")
        return super().__new__(cls, token)


def dumps_with_tokens(obj: object, **kwargs: Any) -> str:
    """Serialize obj like json.dumps, writing each JSONNumberToken verbatim.

    Each token is swapped for a placeholder string, the value is serialized,
    and the quoted placeholder is replaced by the bare token, so the token sits
    exactly where json.dumps would have put the value.
    """
    tokens: list[JSONNumberToken] = []

    def swap(value: object) -> object:
        if isinstance(value, JSONNumberToken):
            tokens.append(value)
            return f"\x00json-number-token-{len(tokens) - 1}\x00"
        if isinstance(value, dict):
            return {k: swap(v) for k, v in value.items()}
        if isinstance(value, list):
            return [swap(v) for v in value]
        return value

    text = json.dumps(swap(obj), **kwargs)
    for index, token in enumerate(tokens):
        quoted = json.dumps(f"\x00json-number-token-{index}\x00")
        if text.count(quoted) != 1:
            raise RuntimeError(f"placeholder for {token!r} did not appear exactly once")
        text = text.replace(quoted, token)
    return text


def py_canonical(obj: object) -> bytes:
    """Canonicalize obj with the Python (rfc8785) oracle."""
    return rfc8785.dumps(obj)


def go_canonical(raw_json: bytes) -> bytes:
    """Canonicalize raw_json with the Go (gowebpki/jcs) oracle."""
    p = subprocess.run(
        [str(GO_ORACLE)], input=raw_json, capture_output=True, check=False
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"go oracle rejected input it should accept: {p.stderr.decode()}"
        )
    return p.stdout


def go_rejects(raw_json: bytes) -> bool:
    """True if the Go oracle refuses to canonicalize raw_json."""
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
    *,
    clause: str,
    rationale: str,
    input_obj: object,
    raw_override: bytes | None = None,
) -> bytes:
    """Build one MUST-ACCEPT vector, cross-checking both oracles for real."""
    raw = (
        raw_override
        if raw_override is not None
        else dumps_with_tokens(input_obj, ensure_ascii=False).encode("utf-8")
    )
    py_out = py_canonical(json.loads(raw.decode("utf-8")))
    go_out = go_canonical(raw)
    if py_out != go_out:
        raise OracleDisagreementError(
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
    *,
    clause: str,
    rejecting_clause: str,
    rejection_layer: str,
    rationale: str,
    raw_text: str,
) -> None:
    """Build one MUST-REJECT vector.

    Requires BOTH independent oracles to refuse the input -- a reject
    vector adjudicated by only one oracle is not adjudicated at all, it is
    one implementation's opinion wearing a two-oracle corpus's credibility.
    (Discovered the hard way: two earlier surrogate-pair vectors passed on
    Python-only agreement while Go's gowebpki/jcs silently substituted
    U+FFFD instead of erroring -- a real oracle disagreement, not a harness
    bug, and exactly what an OR check would hide.)
    """
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


def _write(group_dir: str, vid: str, vector: dict) -> None:
    """Write one vector JSON file into group_dir under OUT_ROOT."""
    d = OUT_ROOT / group_dir
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{vid}.json"
    p.write_text(
        dumps_with_tokens(vector, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {p.relative_to(HERE)}")


def main() -> int:
    """Regenerate the requested groups (default: all five) into OUT_ROOT."""
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
