"""A5 -- number serialization. RFC 8785 sect. 3.2.2.3: numbers are
serialized using the ECMAScript Number::toString algorithm, never a
language's default float formatter. 18 vectors per the design doc's count
table; re-derive the live count from MANIFEST.json.

Every expected byte string here is computed by the two independent
oracles, never hand-derived from a mental model of the ECMA-262 boundary
rules -- that is the entire point of dual-oracle verification: the exact
fixed/exponential switch points do not need to be memorized correctly by
whoever writes the test inputs, only agreed upon by two implementations
that were not written by the same person testing them.

Reject count: 3, not the doc's estimated 4. NaN and +/-Infinity are the
only JSON number values with no ECMAScript Number::toString representation
at all -- every finite double has a well-defined one, so there is no
fourth legitimate canonicalization-layer number rejection to manufacture
without inventing one. Shipping 3 solid vectors beats forcing a 4th.
"""

from gen_layer_a import make_accept, make_reject

GROUP = "a5-number-serialization"


def generate():
    make_accept(
        "A5-001",
        GROUP,
        "RFC8785-3.2.2.3",
        "The a2aproject/A2A#2122 counterexample verbatim (case C4): "
        "0.000001 must serialize as the literal '0.000001', not as '1e-06' (Python's repr "
        "threshold, which is what a2a-python's json.dumps produces and what makes this a real "
        "cross-SDK break).",
        {"tolerance": 0.000001},
    )
    make_accept(
        "A5-002",
        GROUP,
        "RFC8785-3.2.2.3",
        "The a2aproject/A2A#2122 'big' companion value from the same case C4: 1e21 crosses the "
        "ECMAScript fixed/exponential boundary on the large-magnitude side and must serialize "
        "in exponential form.",
        {"big": 1e21},
    )
    make_accept(
        "A5-003",
        GROUP,
        "RFC8785-3.2.2.3",
        "Positive integers serialize with no decimal point and no fractional zeros.",
        {"n": 42},
    )
    make_accept(
        "A5-004",
        GROUP,
        "RFC8785-3.2.2.3",
        "Negative integers keep the sign and otherwise follow the same integer rule.",
        {"n": -17},
    )
    make_accept(
        "A5-005",
        GROUP,
        "RFC8785-3.2.2.3",
        "Zero serializes as the bare digit '0'.",
        {"n": 0},
    )
    make_accept(
        "A5-006",
        GROUP,
        "RFC8785-3.2.2.3",
        "Negative zero is a distinct IEEE 754 bit pattern from positive zero, but "
        "ECMAScript's Number::toString collapses both to the same string '0' -- there is no "
        "'-0' output form.",
        {"n": -0.0},
    )
    make_accept(
        "A5-007",
        GROUP,
        "RFC8785-3.2.2.3",
        "0.1 cannot be represented exactly in IEEE 754 double precision; ECMAScript's "
        "algorithm prints the shortest decimal digit sequence that round-trips back to the "
        "same double, not the full ~17-digit exact binary expansion.",
        {"n": 0.1},
    )
    make_accept(
        "A5-008",
        GROUP,
        "RFC8785-3.2.2.3",
        "A five-significant-digit decimal exercises the shortest-round-trip rule on a value "
        "with more precision than 0.1.",
        {"n": 3.14159},
    )
    make_accept(
        "A5-009",
        GROUP,
        "RFC8785-3.2.2.3",
        "Number.MAX_SAFE_INTEGER (2^53 - 1): the largest integer every JS engine represents "
        "exactly, a natural boundary value for integer serialization.",
        {"n": 9007199254740991},
    )
    make_accept(
        "A5-010",
        GROUP,
        "RFC8785-3.2.2.3",
        "A negative decimal combines the sign rule (A5-004) with fractional shortest-digit "
        "serialization (A5-007) in one value.",
        {"n": -123.456},
    )
    make_accept(
        "A5-011",
        GROUP,
        "RFC8785-3.2.2.3",
        "One order of magnitude below the a2aproject/A2A#2122 case C4 value (A5-001): 0.0000001 (1e-7) "
        "probes the small-magnitude side of the fixed/exponential boundary that 0.000001 sits "
        "just on the fixed side of.",
        {"n": 0.0000001},
    )
    make_accept(
        "A5-012",
        GROUP,
        "RFC8785-3.2.2.3",
        "One order of magnitude below the C4 'big' value (A5-002): 1e20 probes the "
        "large-magnitude side of the same boundary that 1e21 sits just past.",
        {"n": 100000000000000000000.0},
    )
    make_accept(
        "A5-013",
        GROUP,
        "RFC8785-3.2.2.3",
        "0.1 + 0.2 in IEEE 754 double arithmetic does not equal 0.3; this is the resulting "
        "value (0.30000000000000004), a classic case requiring the full shortest-round-trip "
        "digit count rather than a short 'looks clean' rounding.",
        {"n": 0.1 + 0.2},
    )
    make_accept(
        "A5-014",
        GROUP,
        "RFC8785-3.2.2.3",
        "A round integer must not be printed in exponential form just because it has trailing "
        "zeros; 100 stays '100', not '1e2'.",
        {"n": 100},
    )
    make_accept(
        "A5-015",
        GROUP,
        "RFC8785-3.2.2.3",
        "Input syntax is not preserved verbatim: '1E1' (uppercase E, RFC 8259 permits both "
        "cases) and a trailing '.0' both parse to the double values 10 and 1 respectively, and "
        "the canonical form is the ECMAScript string for that VALUE, not a copy of the input "
        "digit sequence -- this vector's input intentionally does not look like its output.",
        {"exp_upper": 1e1, "trailing_zero": 1.0},
        raw_override=b'{"exp_upper": 1E1, "trailing_zero": 1.0}',
    )
    make_reject(
        "A5-REJECT-016",
        GROUP,
        "RFC8785-3.2.2.3",
        rejecting_clause="RFC8785-3.2.2.3",
        rejection_layer="canonicalization",
        rationale="NaN is not a valid RFC 8259 JSON number and has no ECMAScript "
        "Number::toString representation as a JSON token; some lenient parsers accept the bare "
        "word NaN as a non-standard extension, but a conformant canonicalizer must refuse to "
        "emit it rather than pass the extension through.",
        raw_text='{"n": NaN}',
    )
    make_reject(
        "A5-REJECT-017",
        GROUP,
        "RFC8785-3.2.2.3",
        rejecting_clause="RFC8785-3.2.2.3",
        rejection_layer="canonicalization",
        rationale="Infinity is the positive-magnitude sibling of A5-REJECT-016: not valid "
        "JSON, no canonical representation, must be refused rather than passed through by any "
        "parser lenient enough to accept the bare word.",
        raw_text='{"n": Infinity}',
    )
    make_reject(
        "A5-REJECT-018",
        GROUP,
        "RFC8785-3.2.2.3",
        rejecting_clause="RFC8785-3.2.2.3",
        rejection_layer="canonicalization",
        rationale="Negative infinity completes the set: same defect as A5-REJECT-017 with the "
        "sign flipped, confirming the rejection is not specific to the unsigned spelling.",
        raw_text='{"n": -Infinity}',
    )
