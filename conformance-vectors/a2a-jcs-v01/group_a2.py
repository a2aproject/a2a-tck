"""A2 -- signatures field exclusion. a2a spec section 8.4.1 rule 3. Reading
a2a-python's own public source confirms the rule: `card_dict.pop(
'signatures', None)` runs BEFORE canonicalization, because a signature
cannot cover the field that carries itself -- the same self-reference RFC
8785 has no opinion on, since RFC 8785 knows nothing about a2a's
`signatures` field at all. 4 vectors, 2 MUST-REJECT.

This is the one Layer-A group that is NOT pure RFC 8785: RFC 8785 has no
concept of "exclude this key". So the verification shape differs from
A3/A4/A5/A6, and deliberately so -- forcing it through the RFC-8785-only
oracle harness would test the wrong thing:

  MUST-ACCEPT vectors test the PRODUCTION direction: given a full object
  that carries a `signatures` field, the canonical output is the RFC 8785
  canonicalization of the SAME object with `signatures` removed first.
  Both real oracles still compute the actual expected bytes (on the
  post-exclusion object) -- nothing here is hand-derived.

  MUST-REJECT vectors test the CONSUMPTION direction: a byte string
  presented AS the canonical form that still contains a `signatures` key
  violates the exclusion invariant and a conformant verifier must refuse
  it before ever reaching RFC 8785 byte comparison. This is a structural
  check (does the claimed-canonical string still carry `signatures`), not
  an RFC-8785-well-formedness check, which is why it does not go through
  make_reject's oracle-refusal path -- both oracles would happily
  canonicalize a JSON object that happens to have a `signatures` key,
  because RFC 8785 does not forbid it. a2a's OWN rule does.
"""

import json

from gen_layer_a import _write, go_canonical, py_canonical

GROUP = "a2-signatures-exclusion"


def _strip_signatures(obj):
    return {k: v for k, v in obj.items() if k != "signatures"}


def _make_accept_excluding_signatures(vid, rationale, full_input):
    stripped = _strip_signatures(full_input)
    raw = json.dumps(stripped, ensure_ascii=False).encode("utf-8")
    py_out = py_canonical(stripped)
    go_out = go_canonical(raw)
    if py_out != go_out:
        raise RuntimeError(f"{vid}: oracles disagree on the post-exclusion object")
    vector = {
        "id": vid,
        "clause": "a2a-spec-8.4.1-rule-3",
        "spec_ref": "https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements",
        "layer": "canonicalization",
        "disposition": "MUST-ACCEPT",
        "rationale": rationale,
        "input": full_input,
        "expected": {"canonical_utf8_hex": py_out.hex()},
    }
    _write(GROUP, vid, vector)


def _make_reject_signatures_present(vid, rationale, claimed_canonical_bytes: bytes):
    # Structural check, not an oracle-refusal check: does the byte string
    # actually being tested (what a producer WRONGLY emitted as canonical)
    # still carry a top-level "signatures" key. Confirmed against the real
    # parsed object rather than a substring search, so this is not fooled
    # by e.g. a string VALUE that happens to contain the word "signatures".
    obj = json.loads(claimed_canonical_bytes.decode("utf-8"))
    if "signatures" not in obj:
        raise RuntimeError(
            f"{vid}: this is not actually a violating example -- fix the fixture"
        )
    vector = {
        "id": vid,
        "clause": "a2a-spec-8.4.1-rule-3",
        "spec_ref": "https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements",
        "layer": "canonicalization",
        "disposition": "MUST-REJECT",
        "rejecting_clause": "a2a-spec-8.4.1-rule-3",
        "rejection_layer": "canonicalization",
        "rationale": rationale
        + " (confirmed: the input below is valid, well-formed JSON that "
        "parses cleanly -- both RFC 8785 oracles would canonicalize it without complaint -- and "
        "is refused ONLY because it retains the excluded key, which is an a2a-specific rule RFC "
        "8785 itself has no opinion on.)",
        "input_raw": claimed_canonical_bytes.decode("utf-8"),
    }
    _write(GROUP, vid, vector)


def generate():
    _make_accept_excluding_signatures(
        "A2-001",
        "A card carrying a populated `signatures` array canonicalizes as if that key were "
        "absent entirely; the exclusion is unconditional, not conditional on the array being "
        "empty.",
        {
            "name": "Example Agent",
            "capabilities": {"streaming": True, "pushNotifications": False},
            "signatures": [
                {"protected": "eyJhbGciOiJFUzI1NiJ9", "signature": "abc123"}
            ],
        },
    )
    _make_accept_excluding_signatures(
        "A2-002",
        "A card carrying an EMPTY `signatures` array ([]) is excluded the same way as a "
        "populated one (A2-001): exclusion is by key presence, not by whether the value is "
        "'interesting'. Compare directly against A6-001, which established that an empty array "
        "is otherwise a perfectly normal RFC 8785 value elsewhere in a document -- the only "
        "thing special about `signatures` is the key name.",
        {
            "name": "Example Agent",
            "capabilities": {"streaming": True, "pushNotifications": False},
            "signatures": [],
        },
    )
    _make_reject_signatures_present(
        "A2-REJECT-003",
        "A single-signature payload presented as canonical output but still carrying its own "
        "`signatures` array is self-referential: the bytes a signature covers cannot include "
        "the signature that covers them, so any canonical form containing `signatures` is "
        "definitionally wrong regardless of what RFC 8785 alone would say about it.",
        b'{"capabilities":{"pushNotifications":false,"streaming":true},'
        b'"name":"Example Agent",'
        b'"signatures":[{"protected":"eyJhbGciOiJFUzI1NiJ9","signature":"abc123"}]}',
    )
    _make_reject_signatures_present(
        "A2-REJECT-004",
        "Even a `signatures` key holding an empty array must still be rejected in claimed-"
        "canonical output: the exclusion rule is unconditional (A2-002), so its violation is "
        "unconditional too -- an empty array does not make the self-reference acceptable, it is "
        "still the wrong key present in the wrong place.",
        b'{"capabilities":{"pushNotifications":false,"streaming":true},'
        b'"name":"Example Agent","signatures":[]}',
    )
