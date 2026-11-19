# `a2a-card-sign-v01`: Agent Card signature vectors

Layer **C** of the Agent Card canonicalization corpus: which **signatures** a verifier accepts.

| layer | corpus | question |
|---|---|---|
| A | `a2a-jcs-v01` (a2aproject/a2a-tck#228) | RFC 8785 canonicalization and the `signatures` exclusion |
| B | `a2a-jcs-rule1-v01` (a2aproject/a2a-tck#245) | section 8.4.1 rule 1 on bytes, one expectation per resolution |
| C | `a2a-card-sign-v01` (this) | given a signed card, accept or reject |

Layers A and B pin bytes. A card in the wild arrives with a signature, and the verifier has to decide which bytes
that signature covers. This corpus pins that decision.

## Readings

The bytes a card signature covers are read in three ways today:

| reading | what it does | matches |
|---|---|---|
| `rule-1-as-written` | Section 8.4.1 rule 1 on the card as served: a REQUIRED field (proto annotation) stays even at its default value, a field with the `optional` keyword stays when set, any other field at its default value is dropped. Then RFC 8785. | the section's own worked example, which keeps `description: ""` and `skills: []` and omits `extensions: []` |
| `prune-empty` | Empty strings, arrays and objects removed recursively, REQUIRED or not. Then RFC 8785. | a2a-sdk 1.2.1, @a2a-js/sdk 1.3.0 |
| `served-as-is` | The served JSON with `signatures` removed, nothing else. Then RFC 8785. | a2a-go a2acrypto at main 534a60fc |

The generator refuses to write a vector unless `prune-empty` equals the a2a-python and @a2a-js/sdk canonical bytes
and `served-as-is` equals a2a-go's, case by case, so the second and third rows describe the SDKs, not a guess about
them.

In s0 and s1 every card carries every REQUIRED field of `AgentCard`, so Layer B's open point (a REQUIRED field absent
from the input) does not arise there, and on those inputs its `presence-preserving` and `inject-required-defaults`
resolutions both give the `rule-1-as-written` bytes. Group s2 is where it does arise.

## Groups

`s0-control`: one card with no field at its default value, so all three readings give the same bytes.

| id | signer | disposition |
|---|---|---|
| S0-001 | reference | MUST-ACCEPT under every reading |
| S0-002 | a2a-sdk 1.2.1 | MUST-ACCEPT under every reading |
| S0-003 | @a2a-js/sdk 1.3.0 | MUST-ACCEPT under every reading |
| S0-004 | a2a-go main 534a60fc | MUST-ACCEPT under every reading |
| S0-REJECT-005 | reference, card edited after signing | MUST-REJECT under every reading |

These hold whichever way a2aproject/A2A#2122 is settled.

`s1-default-valued`: the control card with one field at its default value. Each case is a pair of vectors, one
signature per distinct canonical form. Under any one reading exactly one vector of the pair is accepted.

| case | vector | accepted under |
|---|---|---|
| `description = ""` (REQUIRED) | S1-001 | rule-1-as-written, served-as-is |
| | S1-002 | prune-empty |
| `skills = []` (REQUIRED) | S1-003 | rule-1-as-written, served-as-is |
| | S1-004 | prune-empty |
| `skills[0].tags = []` (REQUIRED on AgentSkill) | S1-005 | rule-1-as-written, served-as-is |
| | S1-006 | prune-empty |
| `capabilities.extensions = []` (not REQUIRED) | S1-007 | rule-1-as-written, prune-empty |
| | S1-008 | served-as-is |
| `securityRequirements = [{}]` (not REQUIRED, an element that becomes empty) | S1-009 | rule-1-as-written, served-as-is, field-level-prune |
| | S1-010 | prune-empty, rule-1-element-collapse |

S1-009 and S1-010 (added 2026-10-10) carry an array element that becomes empty under recursive removal. Whether such an
element collapses is part of the #2122 question, so the pair names its accepting readings explicitly instead of assuming
an answer: `field-level-prune` removes empty field values but never an array element, `rule-1-element-collapse` applies
rule 1 (served scope) after removing elements that become empty, and under `refuse-empty-element`, the strict verifier reading of the
signer sentence widened on #2122 (issuecomment-6077328276), both vectors are rejected. The pair sits next to the
field-level cases, so a reader that only checks for empty fields agrees with `prune-empty` on S1-003 to S1-008 and
disagrees on S1-009/S1-010, and the set fails it rather than one vector. On every other vector `field-level-prune`
equals `prune-empty` and `rule-1-element-collapse` equals `rule-1-served-scope`; the generator (`vectors_s1e.py`) checks
the first over all 42 earlier cards. Observed 2026-10-10: a2a-sdk 1.2.1 and @a2a-js/sdk 1.3.0 accept S1-010, a2a-go
accepts S1-009.

`refuse-empty-element` rejects both members of the pair, so it fails the MUST-ACCEPT side whichever way 8.4.1 settles.
It is listed to be measured, not adopted as the cautious option. A `field-level-prune` verifier written from the
readings table and importing no SDK (@kuangmi-bit, `tck/conformance/verifiers/field_level_prune.py`, merged in
33a310b) scores 26/26 on s0 to s2 under `field-level-prune` with no false accept, and runs as its own job in the
self-test workflow.

## Group s2: a REQUIRED field absent from the served JSON

Added after the first sweep. The s0 and s1 files are unchanged byte for byte, so a sweep over those 13 vectors stays
valid. Rule 1 says a REQUIRED field "MUST always be present"; for a field the signer never served, that sentence can be
scoped two ways, and s2 makes the two scopes testable against each other:

| reading | what it does | matches |
|---|---|---|
| `rule-1-served-scope` | rule 1 applied to the fields present in the served JSON; an absent field stays absent | the section's worked example (S2-WE-011), and no SDK as shipped; the aeoess/a2a-python candidate at 2491248 (not a release) |
| `rule-1-descriptor-scope` | rule 1 applied by walking the AgentCard descriptor; an absent REQUIRED field is emitted at its default (`""`, `[]`, `{}`) | a2a-python at a2aproject/a2a-python#1287 head cdee28e |

On s0 and s1 both scopes give the `rule-1-as-written` bytes. `prune-empty` and `served-as-is` keep their meaning.

| case | vector | accepted under |
|---|---|---|
| `description` absent | S2-001 | rule-1-served-scope, prune-empty, served-as-is |
| | S2-002 | rule-1-descriptor-scope |
| `version` absent | S2-003 / S2-004 | as above |
| `skills` absent | S2-005 / S2-006 | as above |
| `skills[0].tags` absent | S2-007 / S2-008 | as above |
| `defaultInputModes` absent | S2-009 / S2-010 | as above |
| the worked example, served as printed | S2-WE-011 | rule-1-served-scope only |

The generator (`vectors_s2.py`) refuses a case unless `prune-empty` equals a2a-sdk 1.2.1 and @a2a-js/sdk 1.3.0,
`served-as-is` equals a2a-go, and `rule-1-descriptor-scope` equals a2a-python at #1287, byte for byte. The checks are
recorded in `MANIFEST.json` under `s2_checks`.

## Group s3: fields outside the AgentCard schema

Added after a2aproject/A2A#2122 asked how the served-scope sentence treats a field the served JSON carries but the
schema does not define. Section 5.7 says such fields SHOULD be ignored when parsing; it does not say whether a
signature covers them. The s0, s1 and s2 files are unchanged byte for byte. s3 is scored on its own axis
(`"axis": "unknown-fields"` in each vector) against three readings:

| reading | what it does | matches |
|---|---|---|
| `unknown-retain` | served-scope rule 1 on the defined fields; every undefined field kept verbatim where it was served | a2a-go main 534a60fc; the aeoess/a2a-python candidate at 2491248 (not a release) |
| `unknown-exclude` | every undefined field removed at every depth, then served-scope rule 1 | a2a-sdk 1.2.1, @a2a-js/sdk 1.3.0, a2a-python#1287 cdee28e |
| `unknown-reject` | a card carrying any undefined field is refused | no SDK |

Every s3 card is the s0 control card plus undefined fields, with no defined field at its default value, so the s0 to
s2 readings cannot disagree on the defined fields: each pair differs only in whether the undefined fields are covered.

| case | vector | accepted under |
|---|---|---|
| `url`, `protocolVersion`, `preferredTransport` at the top level (0.3 fields) | S3-001 / S3-002 | unknown-retain / unknown-exclude |
| `provider.legalEntity` | S3-003 / S3-004 | as above |
| `compensation` (an undefined object) | S3-005 / S3-006 | as above |
| `skills[0].costHint` (inside a repeated element) | S3-007 / S3-008 | as above |
| `x-reserved: []` (undefined and empty) | S3-009 / S3-010 | as above |
| S3-002 with `url` replaced after signing | S3-T-011 | unknown-exclude only |
| the first case signed twice, `[exclude, retain]` | S3-D-012 | unknown-retain, unknown-exclude |
| S3-D-012 with `url` replaced after signing | S3-D-013 | unknown-exclude only |

S3-T-011 is the point of the group: under `unknown-exclude` the edited card still verifies, because the edited value was
never covered. S3-D-012 and S3-D-013 are the transition: section 8.4.3 asks a client to verify at least one
signature and allows several, so a signer can carry one signature per form while verifiers move over, and every SDK
above already accepts S3-D-012. S3-D-013 shows the limit: a verifier that accepts a card when either form verifies
accepts the edited card too, so the transition belongs on the signer's side, not the verifier's. The "matches" column is recorded, not assumed: `vectors_s3.py` canonicalizes every case with each SDK
and writes which reading its bytes equal to `MANIFEST.json` under `s3_sdk_forms`.

## Group s4: one field under both its JSON name and its protobuf name

Added after a2aproject/A2A#2122 found that a card can carry one schema field twice, for example `defaultInputModes`
and `default_input_modes`. A parser that accepts both spellings keeps one value; a verifier that canonicalizes the
received JSON keeps both members. The specification at `173695755607` does not address it. A sentence was proposed on
#2122 (issuecomment-5946904114, supported in issuecomment-5947101219):

> A verifier MUST refuse a card in which the same schema field appears under both its JSON name and its protobuf name.

This group is labelled against that proposal, as s3 is labelled against its readings (issuecomment-5947250034). The
specification does not yet require refusal, so accepting a dual-name card shows divergence from the proposal, not
failure against the current text. If the sentence is adopted, the results get pinned to the revision that carries it.
`score.py` prints the group in its own table, and in the proposal column accepting a dual-name card counts as a
divergence (`div=`), not a false accept. S4-REJECT-005 is rejected under every reading, so accepting it is a false
accept (`fa=`) in both columns.

| reading | what it does | matches |
|---|---|---|
| `dual-name-tolerate` | the specification text at 173695755607: canonicalize the received JSON under served scope, both spellings kept as served | a2a-go main 534a60fc; aeoess/a2a-python@2491248 |
| `dual-name-refuse` | the proposed sentence: a card carrying both spellings of one field is refused | aeoess/a2a-python@5f9e52c |

| case | vector | accepted under |
|---|---|---|
| `defaultInputModes` and `default_input_modes` at the top level | S4-001 | dual-name-tolerate |
| `skills[0].inputModes` and `skills[0].input_modes` | S4-002 | dual-name-tolerate |
| `bearerFormat` and `bearer_format` inside a `securitySchemes` map value | S4-003 | dual-name-tolerate |
| the same scheme with one spelling (control) | S4-004 | both |
| the s0 control signed, then `default_input_modes` added after signing | S4-REJECT-005 | neither |

S4-001 to S4-003 are signed over the received JSON with both members. S4-REJECT-005 is the point of the group: under
either reading the added member must break the signature or be refused. A verifier that drops the snake_case spelling
before canonicalizing still verifies it, while a parser that keeps the snake_case value reads `image/png` from a card
whose signature covered `text/plain`. Which form each SDK's canonicalization equals on each case is recorded in
`MANIFEST.json` under `s4_sdk_forms`.

## Scoring a verifier

`score.py` (beside the generator, no dependencies) takes a verifier's accept/reject verdicts and reports, for each
reading, how many of the 24 s0 to s2 vectors it gets right and how many signatures it accepts that the reading rejects. A
verifier that accepts under two readings at once (a transition policy) is scored the same way: on this corpus it
cannot be conformant to any single reading, because every reading-dependent pair has one vector each reading must
reject. A transition policy therefore has to be declared by the verifier; it cannot be inferred from conformance.
The 13 s3 vectors are scored in a second table against `unknown-retain`, `unknown-exclude` and `unknown-reject`.

In a2aproject/a2a-tck, `tck/conformance/card_sign.py` does the same scoring in TCK style and also runs a verifier
directly: `uv run python -m tck.conformance.card_sign --verifier "node verify.mjs {card} {jwks}"` runs the command once
per vector (exit status 0 is an accept), and `--require READING` exits 1 unless the verifier gets every vector of that
reading right with no false accepts, for an SDK's own CI. Without `--verifier` it checks the corpus itself: every file
against `MANIFEST.json`, every recorded canonical form as RFC 8785 output, and every signature over its recorded bytes,
with no third-party package. `make unit-test` runs those checks.

## Observed on 2026-10-01

Not part of the expectations; recorded in `MANIFEST.json` under `observed`. Each SDK's own verifier on each served card:

| vector | a2a-python | a2a-js | a2a-go |
|---|---|---|---|
| S0-001 to S0-004 | accept | accept | accept |
| S0-REJECT-005 | reject | reject | reject |
| S1-001, S1-003, S1-005 | reject | reject | accept |
| S1-002, S1-004, S1-006 | accept | accept | reject |
| S1-007 | accept | accept | reject |
| S1-008 | reject | reject | accept |

The observed column follows directly from the readings table: each SDK accepts the vectors tagged with its own
reading. For s2, `MANIFEST.json` records the same three SDKs plus a2a-python at #1287 under `observed.s2`: the three
shipping SDKs accept S2-001, 003, 005, 007 and 009 and reject the even ones; a2a-python at #1287 does the opposite; none
accepts S2-WE-011.

On 2026-10-02, `observed.s3`: a2a-sdk 1.2.1, @a2a-js/sdk 1.3.0 and a2a-python at #1287 accept S3-002, 004, 006, 008,
010 and S3-T-011 and reject the odd ones; a2a-go accepts the odd ones and rejects the rest, S3-T-011 included.
All four accept S3-D-012; a2a-go rejects S3-D-013 and the other three accept it.

The a2a-python#1287 column records commit cdee28e, the descriptor-scope commit, and nothing later. On 2026-10-02 the
PR head moved to a091c83, which reverts that commit; kuangmi-bit re-measured it as byte-identical to base fad0482 on
all 37 vectors, so at a091c83 every row reads exactly like the a2a-python (a2a-sdk 1.2.1) column
(a2aproject/a2a-python#1287). The column stays as the record of the descriptor reading. It is not the PR's current
behaviour; for the PR head, cite the a2a-python column.

On 2026-10-02, `observed.s4`:

| vector | a2a-python (1.2.1) | a2a-js (1.3.0) | a2a-go | aeoess@2491248 | aeoess@5f9e52c |
|---|---|---|---|---|---|
| S4-001 to S4-003 | reject | reject | accept | accept | reject |
| S4-004 | accept | accept | accept | accept | accept |
| S4-REJECT-005 | reject | **accept** | reject | reject | reject |

a2a-python 1.2.1 and @a2a-js/sdk 1.3.0 reject S4-001 to S4-003 because they canonicalize another form, not because they
refuse the card, and they do not agree with each other on that form: a2a-python takes the snake_case value, @a2a-js/sdk
keeps the camelCase member and drops the other (`s4_sdk_forms`). S4-REJECT-005 separates the two: @a2a-js/sdk 1.3.0
accepts a card whose snake_case member was added after signing, and a parser that takes that member then reads a value
the signature never covered.

## Pinned candidates

A candidate that is not a release can be added as its own column without regenerating any vector:
`observe_pinned.py` runs inside a virtualenv where the candidate is installed from source, refuses to run unless the
source is at the pinned commit with no local change, passes each served card unmodified to the candidate's verifier,
and writes the verdicts beside the SDK columns in `MANIFEST.json` (`observed.results`, `observed.s2`, `observed.s3`),
the pin under `observed.pinned`, and which reading its canonical bytes equal under `s3_sdk_forms`. `--check` reruns and
compares without writing. The verdicts are also in `verdicts_20261002/` for `score.py`.

`aeoess/a2a-python@5f9e52c` (same branch) adds the refusal of a field given under both spellings. On s0 to s3 its 37
verdicts are identical to 2491248; on s4 it is the `dual-name-refuse` column. 2491248 stays the pin for the s0 to s3
numbers published on #2122.

`aeoess/a2a-python@2491248` (branch `candidate/served-scope-1278`, a candidate for a2aproject/A2A#2122): the new entry
point `create_served_card_signature_verifier` takes the received JSON and canonicalizes it with
`canonicalize_served_agent_card`; the existing `create_signature_verifier` is unchanged. Measured on 2026-10-02:

| group | reading | right | false accepts |
|---|---|---|---|
| s0 | every reading | 5/5 | 0 |
| s1 | rule-1-as-written | 8/8 | 0 |
| s2 | rule-1-served-scope | 11/11 | 0 |
| s3 | unknown-retain | 13/13 | 0 |

S3-D-012 is accepted through its retained-form signature, S3-T-011 and S3-D-013 are refused. On every vector it
accepts, its canonical bytes equal the bytes the signature covers, and on all five s3 cases they equal the
`unknown-retain` form. It differs from the a2a-go column only on S1-007, S1-008 (`capabilities.extensions = []`,
not REQUIRED, dropped) and S2-WE-011. In the same install, the unchanged `create_signature_verifier` reads exactly
like the a2a-python (a2a-sdk 1.2.1) column on all 37.

## Key and reproduction

`testkey_jwks.json` holds the public half of a published test key (kid `hs-interop-test-v1`, ES256). The `jku` in
every protected header is an `example.com` placeholder: never fetch it, resolve the key from `testkey_jwks.json` by
`kid`. The private
key is derived from a public phrase given in `MANIFEST.json`, so anyone can re-create it. Reference signatures use
RFC 6979 deterministic ECDSA, so re-running the generator reproduces every reference vector byte for byte; S0-002 to
S0-004 are kept as the SDKs produced them. The key signs test vectors only and is nobody's production key.

Canonical bytes were produced by two independent RFC 8785 implementations, which agree exactly:

- `rfc8785` (PyPI, 0.1.4)
- `gowebpki/jcs` (Go, v1.0.1)

A third, run blind from outside: @giskard09 ran `jcs.py`, a pure RFC 8785 canonicalizer with no AgentCard-aware
pruning, required-field injection or unknown-field exclusion, over all 44 vectors at `8aa795b`
(a2aproject/a2a-tck#246, issuecomment-6133531509). On the 26 vectors governed by the `served-as-is`, `unknown-retain`
and `dual-name-tolerate` readings it reproduces the covered bytes exactly, S3-D-012 included through its
retained-form signature. Those 26 are the 24 vectors accepted under one of those readings plus S0-REJECT-005 and
S4-REJECT-005, whose covered bytes are the served JSON. The other 18 need a reading-aware step that a pure canonicalizer
does not have. So the disagreement in 8.4.1 is about which bytes are covered, not about RFC 8785.

Spec text: a2aproject/A2A `specification/specification.md` at `173695755607` (v1.0.0). REQUIRED set: the
`field_behavior` annotations of `a2a.proto` (details in `MANIFEST.json` under `spec_provenance`).

Generator: `workers/a2a-card-sign/interop-matrix/vectors.py` in ogasurfproject-jpg/horizon-shield, with
`vectors_check.mjs` beside it, an independent WebCrypto check of every hash and signature.

No file here overlaps `a2a-jcs-v01` or `a2a-jcs-rule1-v01`, and nothing depends on the order in which the three
corpora are merged.
