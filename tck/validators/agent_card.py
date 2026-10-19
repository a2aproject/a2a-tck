"""Agent Card protocol binding identifiers (spec Section 12.7)."""

from __future__ import annotations

from rfc3986_validator import validate_rfc3986

from tck.requirements.base import STANDARD_BINDINGS


def is_protocol_binding(value: object) -> bool:
    """Accept standard identifiers or an absolute URI for a custom binding."""
    return isinstance(value, str) and (value in STANDARD_BINDINGS or bool(validate_rfc3986(value, rule="URI")))
