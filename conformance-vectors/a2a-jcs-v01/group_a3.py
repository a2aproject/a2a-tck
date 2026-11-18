"""A3 -- object key ordering.

RFC 8785 sect. 3.2.3: object properties are ordered by comparing their
names as sequences of UTF-16 code units, NOT by Unicode code point and NOT
"lexicographic by key" as the a2a spec's own gloss puts it -- that gloss is
the defect reported at a2aproject/A2A#2122. 12 vectors, 2 MUST-REJECT;
re-derive from MANIFEST.json.

A3-006 is the load-bearing vector: it is the exact counterexample from
that report (case C3), the case where a2a-python (code-point sort) and
a2a-js (UTF-16 sort) produce different bytes for the same card. Any
canonicalizer that sorts by code point instead of UTF-16 code unit fails
this single vector, which is the entire point of shipping it.
"""

import json

from gen_layer_a import make_accept, make_reject


GROUP = "a3-object-key-ordering"


def generate() -> None:
    """Emit all twelve A3 (object key ordering) vectors."""
    make_accept(
        "A3-001",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale="Baseline: keys already in UTF-16 code-unit order pass through unchanged.",
        input_obj={"a": 1, "b": 2, "c": 3},
    )
    make_accept(
        "A3-002",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale="Keys given out of order must be reordered to UTF-16 code-unit order.",
        input_obj={"zebra": 1, "apple": 2, "mango": 3},
    )
    make_accept(
        "A3-003",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale="Case sensitivity: uppercase ASCII (U+0041 'A') sorts before lowercase ASCII (U+0061 'a') as a raw code unit.",
        input_obj={"apple": 1, "Apple": 2},
    )
    make_accept(
        "A3-004",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale="Numeric-looking keys sort as UTF-16 code-unit sequences, not as numbers: '1' < '10' < '2'.",
        input_obj={"10": 1, "2": 2, "1": 3},
    )
    make_accept(
        "A3-005",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale="A BMP character above the ASCII range (U+00E9 'e with acute') sorts after every ASCII key.",
        input_obj={"cafe": 1, "café": 2},
    )
    make_accept(
        "A3-006",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale=(
            "The a2aproject/A2A#2122 counterexample verbatim (case C3): "
            "a key containing U+1F600 (surrogate pair D83D DE00) sorts BEFORE a key containing "
            "U+FF01 (single unit FF01), because D83D < FF01 as raw UTF-16 code units, even though "
            "the code POINT 1F600 is numerically greater than FF01. Sorting by code point instead "
            "of UTF-16 code unit -- what a2a-python's sort_keys=True does -- gets this pair backwards."
        ),
        input_obj={"b\U0001f600key": 1, "b！key": 2},  # noqa: RUF001 -- U+FF01 is the deliberate test input, not a typo
    )
    make_accept(
        "A3-007",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale=(
            "A second astral-vs-high-BMP inversion pair, generalizing A3-006 beyond one example: "
            "U+10000 (surrogate pair D800 DC00) sorts before U+E000 (single unit E000, Private Use "
            "Area) by the same UTF-16-vs-code-point divergence."
        ),
        input_obj={"x\U00010000end": 1, "xend": 2},
    )
    make_accept(
        "A3-008",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale=(
            "Two byte-distinct keys that render identically to a human (precomposed U+00E9 vs the "
            "combining-character sequence 'e' + U+0301) are different code-unit sequences with no "
            "normalization applied by RFC 8785; they sort as the distinct sequences they are, and "
            "the combining form (starts with plain ASCII 'e', U+0065) sorts before the precomposed "
            "form (starts with U+00E9)."
        ),
        input_obj={"café": 1, "café": 2},  # precomposed U+00E9 vs combining form (e + U+0301)
    )
    make_accept(
        "A3-009",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale="The empty string is a valid key and, having zero code units, sorts before every non-empty key.",
        input_obj={"": 1, "a": 2},
    )
    make_accept(
        "A3-010",
        GROUP,
        clause="RFC8785-3.2.3",
        rationale=(
            "Stress case: eleven keys spanning ASCII, digits and mixed case sorted together, "
            "confirming the ordering rule is stable across more than a handful of keys at once."
        ),
        input_obj={
            "Zulu": 1,
            "alpha": 2,
            "Bravo": 3,
            "charlie": 4,
            "Delta": 5,
            "9key": 6,
            "echo": 7,
            "Foxtrot": 8,
            "1key": 9,
            "golf": 10,
            "Hotel": 11,
        },
    )
    make_reject(
        "A3-REJECT-011",
        GROUP,
        clause="RFC8785-3.2.3",
        rejecting_clause="RFC8785-3.2.2.2",
        rejection_layer="canonicalization",
        rationale=(
            "A key containing a lone (unpaired) high surrogate U+D800 with no following "
            "low surrogate is not valid Unicode text and has no well-formed UTF-8 encoding, so it "
            "cannot be assigned a UTF-16 code-unit sort position or emitted as literal UTF-8 (RFC "
            "8785 sect. 3.2.2.2); a conformant canonicalizer must refuse it rather than silently "
            "pass the unpaired surrogate through or substitute a replacement character."
        ),
        raw_text='{"b\\ud800key": 1, "a": 2}',
    )
    make_reject(
        "A3-REJECT-012",
        GROUP,
        clause="RFC8785-3.2.3",
        rejecting_clause="RFC8785-3.2.2.2",
        rejection_layer="canonicalization",
        rationale=(
            "A key containing a lone (unpaired) LOW surrogate U+DC00 with no preceding "
            "high surrogate completes A3-REJECT-011's high-surrogate case with the low-surrogate "
            "half of the pair: equally invalid Unicode, equally unencodable as well-formed UTF-8, "
            "for the same reason."
        ),
        raw_text='{"b\\udc00key": 1, "a": 2}',
    )


if __name__ == "__main__":
    # smoke: confirm the raw JSON literals above are syntactically valid JSON
    # (Python's json.loads accepts lone surrogates in \u escapes, which is
    # exactly why these are schema-valid-but-canonicalization-invalid rather
    # than parser-rejected -- the distinction the design doc requires for a
    # vector to count toward coverage at all).
    for t in ['{"b\\ud800key": 1, "a": 2}', '{"b\\udc00key": 1, "a": 2}']:
        json.loads(t)
    print("raw reject literals are schema-valid JSON, as required")
