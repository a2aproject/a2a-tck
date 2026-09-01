# a2a-jcs-v01: RFC 8785 canonicalization conformance vectors for a2a Agent Card signing

This corpus is an offer to a2aproject/a2a-tck#227. It gives the CARD-SIGN requirements a
language-neutral conformance corpus. That project currently tags those requirements
not-automatable.

The corpus exists because a2a-python and a2a-js canonicalize the same Agent Card into different
bytes. A card signed by one SDK then fails verification under the other. Two independent RFC 8785
implementations adjudicated the difference and agree that a2a-js is conformant on every axis tested
while a2a-python is not. The report, the reproduction steps, and the specification issue this corpus follows from are
at a2aproject/A2A#2122, a2aproject/a2a-python#1174, and a2aproject/a2a-js#627.

## Scope

This corpus covers Layer A only. Layer A is RFC 8785 canonicalization, plus the a2a rule that
excludes the signatures field before canonicalization runs. Layer B (JWS construction) and Layer C
(verification) are not built yet.

One group is missing from Layer A on purpose: field presence. That group tests whether REQUIRED
fields with default values survive canonicalization. The answer is still an open question at
a2aproject/A2A#2122. About a fifth of a full Layer A corpus would need a retraction if that question
resolves the other way. Every vector below is independent of that question and safe to ship now.

| Group | Clause | Count | Reject |
|---|---|---:|---:|
| A2 signatures exclusion | a2a spec 8.4.1 rule 3 | 4 | 2 |
| A3 object key ordering | RFC 8785 3.2.3 | 12 | 2 |
| A4 string serialization | RFC 8785 3.2.2.2 | 15 | 3 |
| A5 number serialization | RFC 8785 3.2.2.3 | 18 | 3 |
| A6 arrays, nesting, literals | RFC 8785 3.2.1, 3.2.2.1 | 8 | 0 |
| Total | | 57 | 10 |

The design doc estimated 56 vectors and 11 rejects for these five groups; the table above and
MANIFEST.json carry the live count. Real oracle runs against real inputs changed two of the
estimated numbers. A4 has 15 accept vectors, not 14. A second astral-plane
character next to the first turned out to be a distinct, useful case, so it stayed. A5 has 3 rejects,
not 4. NaN and positive or negative infinity are the only JSON number values with no ECMAScript
Number toString form at all. Every finite double has one, so a fourth legitimate reject case for
numbers does not exist.

## How each expected byte was produced

No expected byte here came from hand calculation. Every accept vector runs its input through two
independent RFC 8785 implementations, rfc8785 0.1.4 on PyPI for Python and gowebpki/jcs v1.0.1 on
GitHub for Go. Neither project wrote the other. The vector keeps the result only when both
implementations agree, byte for byte. An accept vector never shipped if its two oracles disagreed
on the bytes. The generator raises an error and refuses to write that file.

Reject vectors carry the same rule in the other direction, and it got stricter partway through the
build: both oracles must refuse the input, and one refusal alone stopped being enough. Two early candidates first
shipped on a Python-only refusal: a reversed surrogate pair, and two consecutive high surrogates. The
first version of the generator accepted either oracle's refusal, not both. The Go runner caught the
gap. gowebpki/jcs quietly swaps in a Unicode replacement character for those two malformed
sequences. It does not raise an error. rfc8785 does raise an error for the same input. Both vectors
now use single unpaired surrogates instead, which both oracles genuinely refuse, and the generator
requires that same double refusal before it will write any reject vector at all.

## How to verify this corpus

Run the Python reference runner from the repository root:

    pip install rfc8785
    python3 conformance-vectors/a2a-jcs-v01/run_python.py

Run the Go reference runner:

    cd conformance-vectors/a2a-jcs-v01/oracle-go && go build -o /tmp/a2a-runner ./runner/
    /tmp/a2a-runner /path/to/conformance-vectors/a2a-jcs-v01

Each runner prints one JSON result record. The record holds the corpus digest, the spec commit,
a pass or fail mark per vector, and a coverage count. Each runner exits with a non-zero code on any
failure. Two scripts in this same directory can regenerate the corpus and its manifest:
gen_layer_a.py and gen_manifest.py, and both re-check every vector against both oracles on every
run, so a stale or hand-edited vector gets overwritten the next time either one runs.

## Manifest and digest

MANIFEST.json lists every vector file with its own sha256 hash, sorted by path. The manifest also
carries a corpus digest. That digest is the sha256 hash of the manifest body, taken without the
digest field itself. A digest cannot include its own value. To reproduce it, strip that one field,
re-serialize the file with the same key order, then hash what remains.

## Signing

This corpus is not signed yet. A future version can add a DSSE envelope over an in-toto statement,
giving the corpus tamper evidence and a pinned revision that a third party can re-check later.
Signing status does not block use of this corpus today. Both runners above check the corpus in full
without a signature. A signature would add cryptographic proof that nobody altered a byte after
publication, on top of what the runners already establish by running clean.

## Status

This corpus is offered at a2a-tck#227. giskard09 built their own canonicalizer, argentum-core, from
the RFC 8785 text and has no tie to either a2a-python or a2a-js. giskard09 offered to run these vectors
blind against argentum-core once the non-gated set existed, and that set exists now.
