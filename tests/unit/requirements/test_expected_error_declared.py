"""Registry invariant: a requirement that mandates a specific error declares it.

When a requirement's description says the server ``MUST return <Name>Error``,
that named error is the conformance target.  If the ``RequirementSpec`` does
not declare it via ``expected_error``, tests fall back to accepting *any*
error and a server returning the wrong code passes a MUST it should fail.
This test pins the specific error to the requirement so both the generic
runner and the dedicated tests can assert the exact code.
"""

from __future__ import annotations

import re

from tck.requirements.registry import ALL_REQUIREMENTS


_MUST_RETURN_ERROR = re.compile(
    r"MUST (?:return|result in) (?:a |an )?(\w*Error)\b"
)


def test_named_error_requirements_declare_expected_error() -> None:
    """Every 'MUST return <Name>Error' requirement declares that error."""
    violations = []
    for r in ALL_REQUIREMENTS:
        match = _MUST_RETURN_ERROR.search(r.description)
        if match is None:
            continue
        want = match.group(1)
        have = r.expected_error.name if r.expected_error else None
        if have != want:
            violations.append(f"{r.id}: description mandates {want}, expected_error={have}")
    assert not violations, "Requirements missing their mandated expected_error:\n" + "\n".join(
        violations
    )
