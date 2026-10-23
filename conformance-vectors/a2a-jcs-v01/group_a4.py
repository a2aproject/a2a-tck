r"""A4 -- string serialization.

RFC 8785 sect. 3.2.2.2: string values are emitted as literal UTF-8 outside
the mandatory JSON escape set (quote, backslash, and control characters
below U+0020), NEVER as \uXXXX escapes for ordinary non-ASCII text.
15 vectors, 3 MUST-REJECT; re-derive from MANIFEST.json.

A4-001 is the load-bearing vector: it is the exact counterexample from
a2aproject/A2A#2122 (case C2) -- the case where a2a-python's
ensure_ascii=True default breaks cross-SDK verification for any card with
an accent in it.
"""

from gen_layer_a import make_accept, make_reject


GROUP = "a4-string-serialization"


def generate() -> None:
    """Emit all fifteen A4 (string serialization) vectors."""
    make_accept(
        "A4-001",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "The a2aproject/A2A#2122 counterexample verbatim (case C2): "
            "a non-ASCII scalar (e with acute, U+00E9) is emitted as literal UTF-8 bytes, never as "
            "a \\u00e9 escape. ensure_ascii=True in Python's json.dumps -- a2a-python's actual "
            "default -- produces the escaped form and fails this vector."
        ),
        input_obj={"name": "Café Agent", "description": "Planifie des itinéraires."},
    )
    make_accept(
        "A4-002",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale="Pure ASCII content is the trivial control case: no escaping needed, output equals input.",
        input_obj={"name": "Example Agent"},
    )
    make_accept(
        "A4-003",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "An astral-plane character (U+1F600 GRINNING FACE, outside the Basic Multilingual "
            "Plane, requiring a UTF-16 surrogate pair to represent but a single 4-byte UTF-8 "
            "sequence) is emitted as literal UTF-8, not as a \\ud83d\\ude00 surrogate-pair escape."
        ),
        input_obj={"note": "hello \U0001f600 world"},
    )
    make_accept(
        "A4-004",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "The mandatory escape set is exactly quote, backslash, and control characters below "
            "U+0020: this string exercises all three (a literal quote, a literal backslash, and a "
            "literal newline), each of which MUST still be escaped even though non-ASCII text is "
            "emitted literally."
        ),
        input_obj={"raw": 'a "quoted" \\ path\nwith a newline'},
    )
    make_accept(
        "A4-005",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale="The empty string is a valid scalar value and serializes as a pair of quote characters with nothing between them.",
        input_obj={"empty": ""},
    )
    make_accept(
        "A4-006",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "Every remaining C0 control character (U+0001 through U+001F, excluding the ones with "
            "short escapes like \\n and \\t) must still be escaped as \\u00XX -- control-character "
            "escaping is required regardless of the literal-UTF-8 rule for ordinary text, since "
            "control characters are never literal in a JSON string."
        ),
        input_obj={"ctrl": "abc"},
    )
    make_accept(
        "A4-007",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "A CJK ideograph (U+4E2D, three-byte UTF-8) is emitted as literal UTF-8, the same rule "
            "as A4-001 applied to a script outside the Latin-1 range."
        ),
        input_obj={"label": "中文"},
    )
    make_accept(
        "A4-008",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "U+007F (DELETE) sits immediately above the printable ASCII range and below the C1 "
            "control block; RFC 8785 requires literal UTF-8 for it like any other non-mandatory-"
            "escape character, it is not part of the U+0000-U+001F mandatory escape set."
        ),
        input_obj={"del": "ab"},
    )
    make_accept(
        "A4-009",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "A combining diacritic (U+0301 COMBINING ACUTE ACCENT) immediately following its base "
            "character is ordinary non-ASCII text with no special JSON-string handling; it is "
            "emitted as literal UTF-8 like any other codepoint outside the escape set."
        ),
        input_obj={"combining": "éclair"},
    )
    make_accept(
        "A4-010",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "Right-to-left script content (Arabic, U+0627 ALEF through U+0629 TEH MARBUTA) is "
            "emitted as literal UTF-8 bytes; RFC 8785 has no bidi-aware transform, only byte "
            "identity."
        ),
        input_obj={"rtl": "السلام"},
    )
    make_accept(
        "A4-011",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "Forward slash is explicitly NOT in JSON's mandatory escape set (unlike some JSON "
            "encoders' optional habit of escaping it as \\/) and must be emitted literally."
        ),
        input_obj={"url": "https://example.com/a2a/v1"},
    )
    make_accept(
        "A4-012",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rationale=(
            "A string built entirely from two adjacent astral-plane characters (both requiring "
            "surrogate pairs in UTF-16) confirms multi-character non-BMP content is handled, not "
            "just a single isolated case like A4-003."
        ),
        input_obj={"emoji_pair": "\U0001f600\U0001f601"},
    )
    make_reject(
        "A4-REJECT-013",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rejecting_clause="RFC8785-3.2.2.2",
        rejection_layer="canonicalization",
        rationale=(
            "A lone (unpaired) low surrogate U+DC00 inside a STRING VALUE (not a key, "
            "unlike A3-REJECT-011/012) is not valid Unicode text and has no well-formed UTF-8 "
            "encoding; a conformant canonicalizer must refuse it rather than emit an invalid byte "
            "sequence or silently substitute U+FFFD."
        ),
        raw_text='{"name": "broken \\udc00 value"}',
    )
    make_reject(
        "A4-REJECT-014",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rejecting_clause="RFC8785-3.2.2.2",
        rejection_layer="canonicalization",
        rationale=(
            "A lone low surrogate (U+DC00) embedded mid-string, with ordinary text both "
            "before and after it, is the string-value counterpart to A3-REJECT-012's key-position "
            "case: unpaired, not valid Unicode, no well-formed UTF-8 encoding, and unlike "
            "A4-REJECT-013's simpler isolated case this confirms the defect is caught with real "
            "surrounding content rather than only in a minimal reproduction."
        ),
        raw_text='{"name": "before\\udc00after"}',
    )
    make_reject(
        "A4-REJECT-015",
        GROUP,
        clause="RFC8785-3.2.2.2",
        rejecting_clause="RFC8785-3.2.2.2",
        rejection_layer="canonicalization",
        rationale=(
            "A high surrogate (U+D800) followed by an ordinary BMP character (a plain "
            "letter, not its matching low surrogate) leaves the high surrogate unpaired for "
            "exactly the same reason as A4-REJECT-013/014, just constructed a third way."
        ),
        raw_text='{"name": "\\ud800x"}',
    )
