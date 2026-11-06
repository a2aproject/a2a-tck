#!/usr/bin/env python3
"""Reference runner (Python / rfc8785), and the harness for any Python implementation.

The corpus tests two functions, and MANIFEST.json names them under ``targets``:

* ``rfc8785``, an RFC 8785 primitive that turns one JSON value into canonical
  bytes. The RFC 8785 vectors apply to it: every group except A2.
* ``card-signing-input``, the bytes an Agent Card signature covers: the card
  without its top-level ``signatures`` field, canonicalized. Every vector
  applies to it, the four rule-3 vectors included.

With no options this runs both targets against the reference implementation,
rfc8785 on PyPI. To test another implementation, point the runner at it rather
than editing this file, so the record comes from an unmodified runner at a
known commit::

    python3 run_python.py --canonicalize mypkg.jcs:canonicalize --refusal mypkg.jcs:JCSError
    python3 run_python.py --signing-bytes mypkg.card:signing_bytes --refusal mypkg.jcs:JCSError

A target whose function is not given is reported under ``targetsNotRun``, never
run through the reference, because a signing path assembled here from someone
else's primitive would test this runner's rule-3 handling rather than theirs.

Every vector gets one outcome. ``pass`` is the only passing one. On a MUST-ACCEPT
vector, ``diverged`` means the implementation returned bytes other than the
expected ones, which is the failure that breaks signatures between
implementations without raising anything, and ``refused`` means it raised one of
its declared refusal exceptions. On a MUST-REJECT vector, ``accepted`` means it
returned bytes for input that has none. ``errored`` means it raised something
that is not a declared refusal. Refusal types match exactly; declaring ValueError
does not also declare UnicodeEncodeError or another subclass.

Exit status: 0 when at least one target ran and every vector in it passed, 1 when
any vector failed, 2 when the corpus or an option could not be used.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys

from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable


HERE = Path(__file__).resolve().parent
DEFAULT_VROOT = HERE
SPEC_COMMIT_PINNED = "19598c4"  # a2a-protocol.org/A2A commit this corpus's clauses were read from
SIGNATURES_EXCLUSION_CLAUSE = "a2a-spec-8.4.1-rule-3"
TARGETS = ("rfc8785", "card-signing-input")
OUTCOMES = ("pass", "diverged", "refused", "accepted", "errored")


class CorpusError(Exception):
    """Raised when the corpus or an option cannot be used, so no verdict is possible."""


def load_attr(spec: str) -> Any:
    """Import ``module:attribute`` and return the attribute.

    Args:
        spec: A string of the form ``package.module:name``.

    Returns:
        The named attribute.

    Raises:
        CorpusError: If the string is malformed or the import fails.
    """
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise CorpusError(f"expected module:attribute, got {spec!r}")
    try:
        return getattr(importlib.import_module(module_name), attr)
    except (ImportError, AttributeError) as exc:
        raise CorpusError(f"cannot load {spec!r}: {exc}") from exc


def reference_functions() -> tuple[Callable[[Any], bytes], Callable[[dict], bytes], tuple[type[BaseException], ...]]:
    """Return the reference primitive, signing path and explicit refusal types.

    rfc8785 0.1.4 refuses an object key holding a lone surrogate by letting the
    codec's UnicodeEncodeError through. That type is listed explicitly rather
    than accepted through a broad ValueError declaration.
    """
    import rfc8785  # only the reference run needs it

    def signing_bytes(card: dict) -> bytes:
        """Drop the top-level ``signatures`` field (rule 3), then RFC 8785."""
        return rfc8785.dumps({k: val for k, val in card.items() if k != "signatures"})

    refusals = (rfc8785.CanonicalizationError, rfc8785.FloatDomainError, rfc8785.IntegerDomainError, UnicodeEncodeError)
    return rfc8785.dumps, signing_bytes, refusals


def load_refusals(specs: list[str]) -> tuple[type[Exception], ...]:
    """Load the exact exception types an external adapter promises to raise.

    Raises:
        CorpusError: If no types are declared or a declaration is invalid.
    """
    if not specs:
        raise CorpusError("--refusal is required for an external implementation; name each expected exception type")
    refusals = []
    for spec in specs:
        cls = load_attr(spec)
        if not isinstance(cls, type) or not issubclass(cls, Exception) or cls is Exception:
            raise CorpusError(f"refusal must name a specific Exception subclass, got {spec!r}")
        refusals.append(cls)
    return tuple(refusals)


def run_function(fn: Callable[[Any], bytes], value: Any, refusals: tuple[type[BaseException], ...]) -> tuple[str, Any]:
    """Call the implementation and classify how it returned.

    Returns:
        ``("bytes", output)``, ``("refused", exception)`` or ``("errored", exception)``.
    """
    try:
        out = fn(value)
    except Exception as exc:  # classified as errored, never swallowed
        return ("refused" if type(exc) in refusals else "errored"), exc
    if not isinstance(out, (bytes, bytearray)):
        return "errored", TypeError(f"returned {type(out).__name__}, not bytes")
    return "bytes", bytes(out)


def check_vector(v: dict, fn: Callable[[Any], bytes], refusals: tuple[type[BaseException], ...]) -> tuple[str, str]:
    """Check one vector against the function of a target that owns it.

    Returns:
        The outcome and a detail string.
    """
    if v["disposition"] == "MUST-ACCEPT":
        kind, out = run_function(fn, v["input"], refusals)
        if kind != "bytes":
            return kind, f"raised {type(out).__name__}: {out}"
        want = bytes.fromhex(v["expected"]["canonical_utf8_hex"])
        if out != want:
            return "diverged", f"got {out!r} want {want!r}"
        return "pass", "ok"
    # MUST-REJECT. json.loads accepts every reject input in this corpus (lone
    # surrogates, NaN, Infinity), so the implementation is always the one asked.
    raw = v["input_raw"]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return "errored", f"runner could not parse input_raw, so the implementation was never asked: {exc}"
    kind, out = run_function(fn, parsed, refusals)
    if v["clause"] == SIGNATURES_EXCLUSION_CLAUSE:
        # The input is presented AS a card's signing bytes while still carrying
        # `signatures`. A verifier recomputes the signing bytes from the parsed
        # card and refuses when they differ, so this runs the implementation;
        # a check on the fixture alone would pass whatever it did.
        if kind != "bytes":
            return kind, f"signing path raised on a well-formed card: {type(out).__name__}: {out}"
        if out != raw.encode("utf-8"):
            return "pass", "refused: not this card's signing bytes"
        return "accepted", "recomputed signing bytes equal bytes that still carry 'signatures'"
    if kind == "bytes":
        return "accepted", f"produced {out!r} for input with no canonical form"
    if kind == "refused":
        return "pass", f"refused: {type(out).__name__}"
    return kind, f"raised {type(out).__name__}, which is not a declared refusal: {out}"


def run(vroot: Path, functions: dict[str, Callable[[Any], bytes]], refusals: tuple[type[BaseException], ...]) -> dict:
    """Run every target that has a function and build the result record."""
    try:
        manifest = json.loads((vroot / "MANIFEST.json").read_text(encoding="utf-8"))
        vectors = [json.loads((vroot / e["path"]).read_text(encoding="utf-8")) for e in manifest["vectors"]]
        declared = manifest["targets"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise CorpusError(f"cannot read the corpus at {vroot}: {exc}") from exc
    if set(declared) != set(TARGETS):
        raise CorpusError(f"manifest declares targets {sorted(declared)}, this runner knows {list(TARGETS)}")

    targets: dict[str, dict] = {}
    not_run: dict[str, str] = {}
    results = []
    for target in TARGETS:
        owned = [v for v in vectors if v["clause"] in declared[target]["clauses"]]
        if len(owned) != declared[target]["vectors"]:
            raise CorpusError(f"{target}: manifest says {declared[target]['vectors']} vectors, found {len(owned)}")
        fn = functions.get(target)
        if fn is None:
            not_run[target] = f"no function given for {declared[target]['function']}; {len(owned)} vectors not run"
            continue
        tally = dict.fromkeys(OUTCOMES, 0)
        for v in owned:
            outcome, detail = check_vector(v, fn, refusals)
            tally[outcome] += 1
            results.append({"target": target, "id": v["id"], "outcome": outcome, "detail": detail})
        targets[target] = {
            "vectors": len(owned),
            "passed": tally["pass"],
            "failed": len(owned) - tally["pass"],
            "outcomes": tally,
        }

    return {
        "corpusDigest": manifest["corpusDigest"],
        "specCommit": SPEC_COMMIT_PINNED,
        "targets": targets,
        "targetsNotRun": not_run,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    """Parse options, run the corpus and print the result record."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("vroot", nargs="?", type=Path, default=DEFAULT_VROOT, help="corpus directory")
    parser.add_argument("--canonicalize", metavar="MODULE:FUNC", help="RFC 8785 primitive: JSON value -> bytes")
    parser.add_argument("--signing-bytes", metavar="MODULE:FUNC", help="Agent Card -> the bytes its signature covers")
    parser.add_argument(
        "--refusal",
        metavar="MODULE:CLASS",
        action="append",
        default=[],
        help="exact refusal exception type (repeatable; required for external implementations)",
    )
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path.cwd()))

    try:
        if args.canonicalize is None and args.signing_bytes is None:
            if args.refusal:
                raise CorpusError("--refusal applies to an implementation given with --canonicalize or --signing-bytes")
            canon, signing, refusals = reference_functions()
            functions = {"rfc8785": canon, "card-signing-input": signing}
            implementation = {"rfc8785": "rfc8785:dumps", "card-signing-input": "reference: drop signatures, then rfc8785:dumps"}
            runner = "python/rfc8785"
        else:
            refusals = load_refusals(args.refusal)
            functions, implementation = {}, {}
            for target, spec in (("rfc8785", args.canonicalize), ("card-signing-input", args.signing_bytes)):
                if spec is not None:
                    fn = load_attr(spec)
                    if not callable(fn):
                        raise CorpusError(f"implementation must be callable, got {spec!r}")
                    functions[target] = fn
                    implementation[target] = spec
            runner = "python/run_python.py"
        record = {
            "runner": runner,
            "implementation": implementation,
            "refusal": [f"{c.__module__}:{c.__qualname__}" for c in refusals],
            "refusalMatch": "exact",
        }
        record.update(run(args.vroot, functions, refusals))
    except CorpusError as exc:
        print(f"run_python.py: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(record, indent=2))
    ran = record["targets"]
    return 0 if ran and all(t["failed"] == 0 for t in ran.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
