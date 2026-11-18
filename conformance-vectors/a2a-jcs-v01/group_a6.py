"""A6 -- arrays, nesting, literals.

RFC 8785 sect. 3.2.1 (array/object recursion, order preservation within
arrays) and sect. 3.2.2.1 (literal values: null, true, false). 8 vectors,
0 MUST-REJECT per the design doc's count table -- these are all structural
cases where a CONFORMANT input has one unambiguous canonical form; there is
nothing here for a canonicalizer to legitimately refuse.
"""

from gen_layer_a import make_accept


GROUP = "a6-arrays-nesting-literals"


def generate() -> None:
    """Emit all eight A6 (arrays, nesting, literals) vectors."""
    make_accept(
        "A6-001",
        GROUP,
        clause="RFC8785-3.2.1",
        rationale="An empty array is a valid value and serializes as '[]' with no whitespace.",
        input_obj={"items": []},
    )
    make_accept(
        "A6-002",
        GROUP,
        clause="RFC8785-3.2.1",
        rationale="An empty object is a valid value and serializes as '{}' with no whitespace.",
        input_obj={"config": {}},
    )
    make_accept(
        "A6-003",
        GROUP,
        clause="RFC8785-3.2.1",
        rationale="Arrays preserve input order; RFC 8785 orders object keys, never array elements.",
        input_obj={"matrix": [[1, 2], [3, 4]]},
    )
    make_accept(
        "A6-004",
        GROUP,
        clause="RFC8785-3.2.1",
        rationale="Object nesting recurses the same key-ordering rule at every depth.",
        input_obj={"a": {"b": {"c": 1}}},
    )
    make_accept(
        "A6-005",
        GROUP,
        clause="RFC8785-3.2.2.1",
        rationale=(
            "An array may mix every JSON primitive type; each element serializes per its own "
            "type's rule and array order is preserved regardless of type."
        ),
        input_obj={"mixed": [1, "two", True, False, None, 3.5]},
    )
    make_accept(
        "A6-006",
        GROUP,
        clause="RFC8785-3.2.2.1",
        rationale="The null literal serializes as the bare token 'null'.",
        input_obj={"value": None},
    )
    make_accept(
        "A6-007",
        GROUP,
        clause="RFC8785-3.2.2.1",
        rationale=(
            "Boolean literals serialize as the bare tokens 'true'/'false', and sibling keys still "
            "sort (RFC8785-3.2.3) regardless of value type."
        ),
        input_obj={"flag_true": True, "flag_false": False},
    )
    make_accept(
        "A6-008",
        GROUP,
        clause="RFC8785-3.2.1",
        rationale=(
            "Deep alternation of arrays containing objects containing arrays exercises the "
            "recursion to more than two levels; order is preserved at every array level and keys "
            "sorted at every object level."
        ),
        input_obj={"deep": [{"x": [1, {"y": 2}]}, {"x": []}]},
    )
