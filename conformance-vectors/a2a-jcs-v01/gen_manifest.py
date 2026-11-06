#!/usr/bin/env python3
"""Build MANIFEST.json for the a2a-jcs-v01 corpus.

Every vector's sha256, sorted by path, the function each vector tests, and a
corpus digest that is the sha256 of the manifest body itself.
"""

from __future__ import annotations

import hashlib
import json

from pathlib import Path


HERE = Path(__file__).resolve().parent
VROOT = HERE

#: Clause of the a2a rule that removes the top-level ``signatures`` field from
#: the bytes a card signature covers. RFC 8785 has no notion of that field.
SIGNATURES_EXCLUSION_CLAUSE = "a2a-spec-8.4.1-rule-3"

#: Prefix every RFC 8785 clause carries.
RFC8785_CLAUSE_PREFIX = "RFC8785-"


def build_targets(vector_clauses: list[str]) -> dict[str, dict[str, object]]:
    """Name the two functions this corpus tests and the clauses each one owns.

    An RFC 8785 primitive and an Agent Card signing path are different
    functions, and a run that scores one against the other's vectors reports
    a number about neither. The RFC 8785 vectors apply to both, because the
    signing input of a card with no ``signatures`` field is its canonical form.
    The rule-3 vectors apply to the signing path only.

    Args:
        vector_clauses: The clause of every vector in the corpus, one per vector.

    Returns:
        The ``targets`` block of the manifest.

    Raises:
        ValueError: If a clause belongs to neither function.
    """
    clauses = set(vector_clauses)
    rfc8785_clauses = sorted(c for c in clauses if c.startswith(RFC8785_CLAUSE_PREFIX))
    unowned = clauses - set(rfc8785_clauses) - {SIGNATURES_EXCLUSION_CLAUSE}
    if unowned:
        raise ValueError(f"no target owns clause(s) {sorted(unowned)}")
    owned = {"rfc8785": rfc8785_clauses, "card-signing-input": sorted(clauses)}
    functions = {
        "rfc8785": "RFC 8785 canonical bytes of one JSON value",
        "card-signing-input": "the bytes an Agent Card signature covers: the card without its top-level "
        "signatures field, canonicalized per RFC 8785 (a2a spec 8.4.1 rules 2 and 3)",
    }
    return {
        name: {
            "function": functions[name],
            "clauses": owned[name],
            "vectors": sum(1 for c in vector_clauses if c in owned[name]),
        }
        for name in ("rfc8785", "card-signing-input")
    }


def main() -> None:
    """Build MANIFEST.json from every vector file under VROOT."""
    entries = []
    vector_clauses = []
    for f in sorted(VROOT.glob("*/*.json")):
        raw = f.read_bytes()
        vector_clauses.append(json.loads(raw)["clause"])
        entries.append({"path": str(f.relative_to(VROOT)), "sha256": hashlib.sha256(raw).hexdigest()})
    entries.sort(key=lambda e: e["path"])

    accept = sum(1 for e in entries if "REJECT" not in e["path"])
    reject = sum(1 for e in entries if "REJECT" in e["path"])

    manifest_body = {
        "corpus": "a2a-jcs-v01",
        "suite": "a2a-agent-card-canonicalization-conformance",
        "specRef": "https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements",
        "layer": "canonicalization",
        "scope": "Layer A only (RFC 8785 canonicalization + a2a signatures-exclusion); "
        "field-presence vectors (spec section 8.4.1 rule 1) are deliberately excluded "
        "pending resolution of a2aproject/A2A#2122's rule-1 question.",
        "oracles": ["rfc8785 (PyPI, 0.1.4)", "gowebpki/jcs (Go, v1.0.1)"],
        "counts": {"accept": accept, "reject": reject, "total": len(entries)},
        "groups": sorted({e["path"].split("/")[0] for e in entries}),
        "targets": build_targets(vector_clauses),
        "vectors": entries,
    }
    manifest_bytes = json.dumps(manifest_body, indent=2, sort_keys=False).encode(
        "utf-8"
    )
    corpus_digest = hashlib.sha256(manifest_bytes).hexdigest()

    manifest_body["corpusDigest"] = corpus_digest
    out = VROOT / "MANIFEST.json"
    out.write_text(
        json.dumps(manifest_body, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {out}")
    print(f"corpusDigest={corpus_digest}")
    print(f"counts: accept={accept} reject={reject} total={len(entries)}")
    for name, target in manifest_body["targets"].items():
        print(f"target {name}: {target['vectors']} vectors")


if __name__ == "__main__":
    main()
