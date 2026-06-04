"""Cross-transport expected-error validator.

Validates that a transport response matches the expected ErrorBinding
from a requirement specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tck.requirements.base import ErrorBinding


def validate_expected_error(
    response: Any,
    transport: str,
    expected: ErrorBinding,
) -> list[str]:
    """Validate that a response matches the expected error binding.

    Returns:
        A list of error strings (empty means validation passed).
    """
    if response.success:
        return [f"Expected {expected.name} but operation succeeded"]

    expected_code = expected.expected_code(transport)
    actual_code = response.error_code
    if expected_code is not None and actual_code != expected_code:
        return [
            f"Expected error code {expected_code} "
            f"({expected.name}), got {actual_code}"
        ]

    return []
