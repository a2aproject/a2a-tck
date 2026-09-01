#!/usr/bin/env python3
"""Build MANIFEST.json for the a2a-jcs-v01 corpus.

Every vector's sha256, sorted by id, and a corpus digest that is the
sha256 of the manifest body itself.
"""

import hashlib
import json

from pathlib import Path


HERE = Path(__file__).resolve().parent
VROOT = HERE


def main() -> None:
    """Build MANIFEST.json from every vector file under VROOT."""
    entries = []
    for f in sorted(VROOT.glob("*/*.json")):
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        entries.append({"path": str(f.relative_to(VROOT)), "sha256": digest})
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


if __name__ == "__main__":
    main()
