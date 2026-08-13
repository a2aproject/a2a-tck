"""A6 -- arrays, nesting, literals. RFC 8785 sect. 3.2.1 (array/object
recursion, order preservation within arrays) and sect. 3.2.2.1 (literal
values: null, true, false). 8 vectors, 0 MUST-REJECT per the design doc's
count table -- these are all structural cases where a CONFORMANT input has
one unambiguous canonical form; there is nothing here for a canonicalizer
to legitimately refuse."""

from gen_layer_a import make_accept

GROUP = "a6-arrays-nesting-literals"


def generate():
    make_accept(
        "A6-001",
        GROUP,
        "RFC8785-3.2.1",
        "An empty array is a valid value and serializes as '[]' with no whitespace.",
        {"items": []},
    )
    make_accept(
        "A6-002",
        GROUP,
        "RFC8785-3.2.1",
        "An empty object is a valid value and serializes as '{}' with no whitespace.",
        {"config": {}},
    )
    make_accept(
        "A6-003",
        GROUP,
        "RFC8785-3.2.1",
        "Arrays preserve input order; RFC 8785 orders object keys, never array elements.",
        {"matrix": [[1, 2], [3, 4]]},
    )
    make_accept(
        "A6-004",
        GROUP,
        "RFC8785-3.2.1",
        "Object nesting recurses the same key-ordering rule at every depth.",
        {"a": {"b": {"c": 1}}},
    )
    make_accept(
        "A6-005",
        GROUP,
        "RFC8785-3.2.2.1",
        "An array may mix every JSON primitive type; each element serializes per its own type's rule and array order is preserved regardless of type.",
        {"mixed": [1, "two", True, False, None, 3.5]},
    )
    make_accept(
        "A6-006",
        GROUP,
        "RFC8785-3.2.2.1",
        "The null literal serializes as the bare token 'null'.",
        {"value": None},
    )
    make_accept(
        "A6-007",
        GROUP,
        "RFC8785-3.2.2.1",
        "Boolean literals serialize as the bare tokens 'true'/'false', and sibling keys still sort (RFC8785-3.2.3) regardless of value type.",
        {"flag_true": True, "flag_false": False},
    )
    make_accept(
        "A6-008",
        GROUP,
        "RFC8785-3.2.1",
        "Deep alternation of arrays containing objects containing arrays exercises the recursion to more than two levels; order is preserved at every array level and keys sorted at every object level.",
        {"deep": [{"x": [1, {"y": 2}]}, {"x": []}]},
    )
