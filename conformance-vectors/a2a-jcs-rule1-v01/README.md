# `a2a-jcs-rule1-v01` — Agent Card field-presence vectors

Layer **B** of the Agent Card canonicalization corpus: spec section 8.4.1 **rule 1**
(field presence and default-value handling). Layer A — RFC 8785 canonicalization
proper and the `signatures`-exclusion rule — is `conformance-vectors/a2a-jcs-v01`
(a2aproject/a2a-tck#228).

## Why this corpus is separate

Rule 1 is under-determined as written for one case: a **REQUIRED** field that is
**absent from the input**. The section says REQUIRED fields "MUST always be present,
even if the field value matches the default", but its own worked example omits four
REQUIRED fields (`supportedInterfaces`, `version`, `defaultInputModes`,
`defaultOutputModes`) and prints a canonical form without them. Discussion:
a2aproject/A2A#2122.

A byte-level corpus cannot decide that question, and it should not pretend to. What it
can do — and what this corpus does — is **pin the bytes each candidate resolution
implies**, as one expectation per resolution, so that whichever wording is adopted
already has its result recorded.

## Reading the vectors

Each vector carries a `resolution` field naming the reading it encodes:

| resolution | meaning |
|---|---|
| `presence-preserving` | Keep what the input carried; drop a non-REQUIRED empty repeated field per rule 1; do **not** materialise absent REQUIRED fields. |
| `inject-required-defaults` | Materialise the REQUIRED set before canonicalization, unconditionally (`""` / `[]` per type). |
| `strict-presence-validation` | Refuse an input lacking REQUIRED fields (`MUST-REJECT`). |

Vectors are grouped in **pairs with the same input** (`R1-001`/`R1-002`,
`R1-003`/`R1-004`) whose expectations are mutually exclusive: exactly one of each pair
applies once the wording is settled. `R1-REJECT-005` carries the third reading.

`R1-001` is a control on the corpus setup itself: its input is the section's own
fragment and its expected bytes are, byte for byte, the canonical form the
specification prints for that fragment.

## Settled names

The two resolutions above are the two rule-1 readings under discussion in
a2aproject/A2A#2122, which now names them directly. The mapping is recorded here so the
corpus and that discussion share one vocabulary:

| this corpus | a2aproject/A2A#2122 | wording |
|---|---|---|
| `presence-preserving` | `rule-1-served-scope` | "The rules apply to the fields present in the JSON being signed or verified. A field absent from that JSON MUST NOT be added." |
| `inject-required-defaults` | `rule-1-descriptor-scope` | The REQUIRED set is applied against the descriptor, so an absent REQUIRED field is materialised at its type default. |
| `strict-presence-validation` | not adopted | An input lacking REQUIRED fields is refused. |

The vectors are unchanged, and so are their digests: they pin bytes, and the bytes of
each resolution are the same under either vocabulary. `MANIFEST.json` carries the same
mapping in `settled_reading.names` for machine use.

Where every card carries every REQUIRED field — the `s0` and `s1` groups of the Layer C
corpus (a2aproject/a2a-tck#246) — the two rule-1 readings coincide. The divergence is
confined to inputs with an absent REQUIRED field, which is `R1-003`/`R1-004` here and
the `s2` group there.

## Two stages, not one

`expected.canonical_utf8_hex` is the result of **rule 1 processing followed by RFC
8785 canonicalization** — not JCS alone. `capabilities.extensions: []` in `R1-001`'s
input is dropped by rule 1 before JCS runs, which is why the raw input canonicalizes
to something else. Vectors that conflate the two stages measure the wrong thing.

## Oracles

Every expected byte string was produced by two independent implementations, and both
agree exactly:

- `rfc8785` (PyPI, 0.1.4)
- `gowebpki/jcs` (Go, v1.0.1)

Provenance of the spec facts used here: `docs/specification.md` at commit
`f63dbb482719`; the REQUIRED set is transcribed from the proto annotations in
`specification/a2a.proto` (`AgentCard`), not from prose.
