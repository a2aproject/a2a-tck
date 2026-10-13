# a2a-jcs-v01: RFC 8785 canonicalization conformance vectors for a2a Agent Card signing

This corpus is an offer to a2aproject/a2a-tck#227. It gives the CARD-SIGN requirements a
language-neutral conformance corpus. That project currently tags those requirements
not-automatable.

The corpus exists because a2a-python and a2a-js canonicalized the same Agent Card into different
bytes, so a card signed by one SDK failed verification under the other. Two independent RFC 8785
implementations adjudicated the difference and agreed that a2a-js was conformant on every axis
tested while a2a-python was not. The report, the reproduction steps, and the specification issue
this corpus follows from are at a2aproject/A2A#2122, a2aproject/a2a-python#1174, and
a2aproject/a2a-js#627.

a2a-python fixed the serializer in a2a-sdk 1.1.4 (a2aproject/a2a-python#1193, which closed #1174).
The fix replaced `json.dumps(..., sort_keys=True)` with an RFC 8785 serializer,
`a2a.utils._jcs.canonicalize`, and its test suite carries the 57 vectors of the previous revision
of this corpus. On 2026-10-12, a2a-sdk 1.1.4 and 1.2.2, the latest release, were run through the
unmodified run_python.py at this revision. Both give the same results:

| a2a-sdk | `rfc8785` (54) | `card-signing-input` (58) |
|---|---:|---:|
| 1.1.3, before the fix | 30 | 28 |
| 1.1.4 and 1.2.2 | 54 | 52 |

The signing path was `_canonicalize_agent_card`, given the card as a dict in place of the
AgentCard message. Before it serializes, it removes empty strings, empty arrays, empty objects and
null values, null array elements included. That step accounts for the six it misses: A4-005,
A6-001, A6-002, A6-005, A6-006 and A6-008. With the step taken out, it passes all 58.

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
| A5 number serialization | RFC 8785 3.2.2.3 | 19 | 3 |
| A6 arrays, nesting, literals | RFC 8785 3.2.1, 3.2.2.1 | 8 | 0 |
| Total | | 58 | 10 |

The design doc estimated 56 vectors and 11 rejects for these five groups; the table above and
MANIFEST.json carry the live count. Real oracle runs against real inputs changed two of the
estimated numbers. A4 has 15 accept vectors, not 14. A second astral-plane
character next to the first turned out to be a distinct, useful case, so it stayed. A5 has 3 rejects,
not 4. NaN and positive or negative infinity are the only JSON number values with no ECMAScript
Number toString form at all. Every finite double has one, so a fourth legitimate reject case for
numbers does not exist. A5 later gained one accept vector the design doc did not list, A5-019 (see
Status).

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

The corpus tests two functions, and MANIFEST.json names them under `targets`. Score each
implementation against the function it provides:

| Target | Function | Vectors |
|---|---|---:|
| `rfc8785` | an RFC 8785 primitive: one JSON value to canonical bytes | 54 (A3 to A6) |
| `card-signing-input` | the bytes a card signature covers: the card without its top-level `signatures` field, canonicalized | 58 (all) |

The four A2 vectors test rule 3, which RFC 8785 has no notion of, so a primitive that is correct
fails them by design. A card with no `signatures` field signs as its canonical form, so the
signing path owns the RFC 8785 vectors as well. A run scored against the wrong target reports a
number about neither function.

Run the Python reference runner from the repository root:

    pip install rfc8785
    python3 conformance-vectors/a2a-jcs-v01/run_python.py

To test another Python implementation, name its functions instead of editing the runner, so the
record comes from an unmodified runner at a known commit:

    python3 conformance-vectors/a2a-jcs-v01/run_python.py --canonicalize mypkg.jcs:canonicalize \
        --refusal mypkg.jcs:JCSError
    python3 conformance-vectors/a2a-jcs-v01/run_python.py --signing-bytes mypkg.card:signing_bytes \
        --refusal mypkg.jcs:JCSError

A target whose function is not given is listed under `targetsNotRun` with its vector count. It is
never run through the reference, because a signing path assembled from someone else's primitive
would test this runner's rule-3 handling rather than theirs. External implementations must name
their refusal exceptions with `--refusal` (repeatable). Types match exactly: `builtins:ValueError`
does not include `UnicodeEncodeError` or a custom subclass. Name each type the implementation
promises to raise. An omitted, invalid or catch-all declaration stops the run with exit status 2.

The Python record includes `refusal` and `refusalMatch: "exact"`. Keep those fields alongside
each reported score. The reference run explicitly lists rfc8785's error types and
`UnicodeEncodeError`, which rfc8785 0.1.4 raises for lone surrogates in object keys. That known
oracle behavior does not become an external adapter's default error contract.

Run the Go reference runner:

    cd conformance-vectors/a2a-jcs-v01/oracle-go && go build -o /tmp/a2a-runner ./runner/
    /tmp/a2a-runner /path/to/conformance-vectors/a2a-jcs-v01

Both runners print one JSON record of the same shape: the corpus digest, the spec commit, a tally
per target, and one outcome per vector per target. Only `pass` passes:

| Outcome | Disposition | Meaning |
|---|---|---|
| `diverged` | MUST-ACCEPT | returned bytes other than the expected ones, silently |
| `refused` | MUST-ACCEPT | raised a declared refusal instead of producing bytes |
| `accepted` | MUST-REJECT | returned bytes for input that has no canonical form, or reproduced signing bytes that still carry `signatures` |
| `errored` | either | raised something other than a declared refusal, or could not be asked |

`diverged` is the outcome that breaks signatures between implementations without an error, so
it is counted apart from `refused`, which fails closed. Each runner exits 0 when at least one
target ran and every vector in it passed, 1 on any failure, and 2 when the corpus or an option
could not be used.

Two scripts in this directory regenerate the corpus. gen_layer_a.py rebuilds every vector and
re-checks it against both oracles on every run, so a stale or hand-edited vector is overwritten
the next time it runs. gen_manifest.py rebuilds MANIFEST.json, its `targets` block and the
corpus digest from the vector files.

## Manifest and digest

MANIFEST.json lists every vector file with its own sha256 hash, sorted by path. Its last member,
`corpusDigest`, is the sha256 of the manifest without that member, over the exact bytes
gen_manifest.py hashes: Python's `json.dumps(body, indent=2)` encoded as UTF-8, where `body` is the
manifest without `corpusDigest` and its other members keep the order the file lists them. That is
two spaces of indentation per level, `": "` between a member name and its value, non-ASCII
characters escaped as `\uXXXX`, and no newline after the closing brace. Those bytes are the file's
own bytes with the `corpusDigest` line, the comma before it and the final newline removed, so the
digest can be recomputed with or without a JSON library. From the repository root, either line
prints it:

    python3 -c 'import json,hashlib; m=json.load(open("conformance-vectors/a2a-jcs-v01/MANIFEST.json")); m.pop("corpusDigest"); print(hashlib.sha256(json.dumps(m, indent=2).encode()).hexdigest())'

    sed '$d' conformance-vectors/a2a-jcs-v01/MANIFEST.json | sed '$d' | sed '$ s/,$//' | { cat; printf '}'; } | sha256sum

(`shasum -a 256` in place of `sha256sum` on macOS.) The digest is not RFC 8785 applied to the
manifest: a canonical form, sorted keys, a compact dump or a trailing newline each gives a
different value.

## Signing

This corpus is not signed yet, but the design is not hypothetical. agent-evidence-vectors publishes
it at tag v0.12.0: https://github.com/probityai/agent-evidence-vectors. A digest list covers every
vector. It is signed offline with a static Ed25519 key committed beside the corpus, and an RFC 3161
authority timestamps it. Nothing goes to a transparency log, so a consumer verifies offline. If
signing lands here, that is the shape to copy.

Signing status does not block use of this corpus today: both runners above check it in full without
a signature, and a signature would add cryptographic proof that nobody altered a byte after
publication, on top of what the runners establish by running clean.

## Status

This corpus is offered at a2a-tck#227. giskard09 built their own canonicalizer, argentum-core, from
the RFC 8785 text and has no tie to either a2a-python or a2a-js. They ran these 57 vectors blind
against it on 2026-08-20, before opening the generators, and reported 57 of 57:
https://github.com/a2aproject/a2a-tck/pull/228#issuecomment-5359047401.

After commit 5cf977d made the rule-3 rejects run the implementation, giskard09 re-ran the corpus. The
new harness refuses when the recomputed signing bytes differ from the presented ones. It reported
57 of 57 again against argentum-core at f8c28c9, and all four A2 vectors fail when the signing path
keeps the signatures field: https://github.com/a2aproject/a2a-tck/pull/228#issuecomment-5794700728.

MolTrust merged recurring CI for all three of its canonicalization paths at
https://github.com/MoltyCel/moltrust-api/pull/505. On 2026-10-01, MoltyCel corrected its earlier
57/57 verify result: five lone-surrogate cases had raised `UnicodeEncodeError` rather than the
declared `CardVerificationError`. The implementation was fixed, and the latest runs reported
53/53 for the raw primitive and 57/57 for both card paths. Its rule-3 negative control failed
all four A2 vectors. The correction and pins are at
https://github.com/a2aproject/A2A/pull/1882#issuecomment-5932794122.

The runner now requires explicit, exact refusal types. Regression tests cover those five
surrogate cases and prove that unexpected exceptions produce `errored` results and a nonzero
exit status. No vector bytes, dispositions or corpus digest changed.

On 2026-10-11 the corpus gained A5-019, the integer spelling of negative zero, `{"n": -0}`. Its
expected bytes are `{"n":0}`, the same as for A5-006, and both oracles agree. A5-006 spells
negative zero as `-0.0`, which parsers read as a double. `-0` is an integer token, and an
implementation that keeps integer tokens as written emits `-0` instead. Two JSON digest readers
measured on the W3C public-agent-conformance list split on exactly this input, one writing `0`
and the other `-0`: https://lists.w3.org/Archives/Public/public-agent-conformance/2026Oct/0038.html.
The 57 earlier vectors are unchanged, byte for byte. The counts and the corpus digest changed, so
the runs above scored 57 vectors, and a run against this revision scores 58 (54 for the `rfc8785`
target).

Of the 16 A5 accept vectors, six tell a canonicalizer that writes each number by its value from
one that passes number tokens through as written: A5-001 (`1e-06`), A5-006 (`-0.0`), A5-011
(`1e-07`), A5-012 (`1e+20`), A5-015 (`10.0` and `1.0`) and A5-019 (`-0`). The other ten are
already spelled in the input the way RFC 8785 writes them, so a pass-through implementation also
passes them; they are controls for the number group, not cases of it.
