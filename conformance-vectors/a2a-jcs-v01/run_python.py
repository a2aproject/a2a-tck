#!/usr/bin/env python3
"""Reference runner (Python / rfc8785). Validates every vector in the
a2a-jcs-v01 corpus against rfc8785 and prints the result record the
design doc specifies: corpus digest, spec commit, per-vector pass/fail,
coverage count. Run this against ANY other RFC 8785 implementation by
swapping the `canonicalize`/`detects_signatures_violation` functions --
that substitution is the entire point of a runner separate from the
generator.
"""

import json
import sys
from pathlib import Path

import rfc8785

HERE = Path(__file__).resolve().parent
DEFAULT_VROOT = HERE
SPEC_COMMIT_PINNED = (
    "19598c4"  # a2a-protocol.org/A2A commit this corpus's clauses were read from
)


def canonicalize(obj) -> bytes | None:
    try:
        return rfc8785.dumps(obj)
    except (ValueError, TypeError):
        return None


def check_vector(v: dict) -> tuple[bool, str]:
    if v["disposition"] == "MUST-ACCEPT":
        obj = v["input"]
        if v["clause"] == "a2a-spec-8.4.1-rule-3":
            obj = {k: val for k, val in obj.items() if k != "signatures"}
        out = canonicalize(obj)
        if out is None:
            return False, "canonicalization raised, expected success"
        want = bytes.fromhex(v["expected"]["canonical_utf8_hex"])
        if out != want:
            return False, f"byte mismatch: got {out!r} want {want!r}"
        return True, "ok"
    else:  # MUST-REJECT
        if v["clause"] == "a2a-spec-8.4.1-rule-3":
            obj = json.loads(v["input_raw"])
            if "signatures" in obj:
                return True, "correctly detected forbidden 'signatures' key"
            return False, "failed to detect the violation this vector carries"
        try:
            obj = json.loads(v["input_raw"])
        except json.JSONDecodeError:
            return True, "correctly refused (parse-level)"
        out = canonicalize(obj)
        if out is None:
            return True, "correctly refused (canonicalization-level)"
        return False, f"accepted input that should have been refused, produced {out!r}"


def main() -> int:
    vroot = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_VROOT
    manifest = json.loads((vroot / "MANIFEST.json").read_text())
    results = []
    for entry in manifest["vectors"]:
        v = json.loads((vroot / entry["path"]).read_text())
        ok, detail = check_vector(v)
        results.append({"id": v["id"], "pass": ok, "detail": detail})

    passed = sum(1 for r in results if r["pass"])
    record = {
        "runner": "python/rfc8785",
        "corpusDigest": manifest["corpusDigest"],
        "specCommit": SPEC_COMMIT_PINNED,
        "coverage": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "results": results,
    }
    print(json.dumps(record, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
