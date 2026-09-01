"""RFC 8785 JSON Canonicalization Scheme, as required for Agent Card signing.

Specification Section 8.4.1 requires that Agent Card content be canonicalized
with JCS before it is signed, and that the ``signatures`` field be excluded
from the content being signed.  This module implements both rules so that the
TCK can compute the canonical signing payload itself instead of trusting a
server to have computed it correctly.

Number formatting follows ECMAScript ``Number.prototype.toString`` as RFC 8785
Section 3.2.2.3 requires.  Object keys are ordered by UTF-16 code unit, not by
Unicode code point (RFC 8785 Section 3.2.3); the two orders disagree whenever a
key mixes astral-plane characters with characters in U+E000..U+FFFF, because
astral characters are represented by surrogate code units that sort lower.

This implementation is held to the ``a2a-jcs-v01`` conformance corpus under
``conformance-vectors/`` by ``tests/unit/canonicalization/test_jcs_vectors.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Mapping


#: Agent Card field that Section 8.4.1 rule 3 excludes from the signed content.
SIGNATURES_FIELD = "signatures"

# RFC 8785 Section 3.2.2.2: only code points below U+0020 are escaped; every
# other character, including U+007F, is emitted literally as UTF-8.
_MIN_UNESCAPED_CODE_POINT = 0x20

# ECMAScript Number::toString switches to exponential notation outside these
# bounds on the decimal exponent (ECMA-262, Number::toString step 5).
_ES6_MAX_FIXED_EXPONENT = 21
_ES6_MIN_FRACTION_EXPONENT = -6

# Two-character escapes mandated by RFC 8785 Section 3.2.2.2.
_SHORT_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class CanonicalizationError(ValueError):
    """Raised when a value has no canonical RFC 8785 representation.

    A conformant canonicalizer must refuse such input rather than emit
    approximate bytes; the corpus's MUST-REJECT vectors assert exactly that.
    """


def _reject_unencodable(value: str, role: str) -> None:
    """Reject a string that is not well-formed Unicode text.

    Args:
        value: The string to check.
        role: Either ``"key"`` or ``"string"``, used in the error message.

    Raises:
        CanonicalizationError: If the string contains an unpaired surrogate.
    """
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError(
            f"{role} contains an unpaired surrogate and has no well-formed "
            f"UTF-8 encoding (RFC 8785 section 3.2.2.2): {value!r}"
        ) from exc


def _utf16_sort_key(key: str) -> bytes:
    """Return the sort key that orders object keys by UTF-16 code unit.

    Big-endian UTF-16 bytes compare in exactly UTF-16 code unit order, which
    is what RFC 8785 Section 3.2.3 specifies.

    Args:
        key: The object key.

    Returns:
        The key encoded as big-endian UTF-16.

    Raises:
        CanonicalizationError: If the key contains an unpaired surrogate.
    """
    try:
        return key.encode("utf-16-be")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError(
            f"object key contains an unpaired surrogate and cannot be assigned "
            f"a UTF-16 sort position (RFC 8785 section 3.2.3): {key!r}"
        ) from exc


def _shortest_digits(value: float) -> tuple[str, int]:
    """Decompose a positive finite float into shortest digits and exponent.

    ``repr`` already produces the shortest decimal string that round-trips,
    which is the digit sequence ECMAScript's Number::toString is defined over.

    Args:
        value: A strictly positive, finite float.

    Returns:
        A tuple ``(digits, n)`` where ``digits`` has no leading or trailing
        zeros and the represented value is ``0.digits * 10**n``.
    """
    mantissa, _, exponent_text = repr(value).partition("e")
    exponent = int(exponent_text) if exponent_text else 0
    integer_text, _, fraction_text = mantissa.partition(".")

    digits = integer_text + fraction_text
    position = len(integer_text) + exponent

    leading = 0
    while leading < len(digits) - 1 and digits[leading] == "0":
        leading += 1
        position -= 1
    digits = digits[leading:].rstrip("0") or "0"

    return digits, position


def _es6_number_to_string(value: float) -> str:
    """Format a finite float exactly as ECMAScript ``Number.prototype.toString`` does.

    Args:
        value: A finite float.

    Returns:
        The ECMAScript string form, e.g. ``"1e+21"``, ``"0.000001"``, ``"100"``.
    """
    if value == 0:
        # Covers negative zero, which ECMAScript renders as "0".
        return "0"
    if value < 0:
        return "-" + _es6_number_to_string(-value)

    digits, position = _shortest_digits(value)
    count = len(digits)

    if count <= position <= _ES6_MAX_FIXED_EXPONENT:
        return digits + "0" * (position - count)
    if 0 < position <= _ES6_MAX_FIXED_EXPONENT:
        return f"{digits[:position]}.{digits[position:]}"
    if _ES6_MIN_FRACTION_EXPONENT < position <= 0:
        return "0." + "0" * (-position) + digits

    exponent = position - 1
    sign = "+" if exponent >= 0 else "-"
    stem = digits if count == 1 else f"{digits[0]}.{digits[1:]}"
    return f"{stem}e{sign}{abs(exponent)}"


def _serialize_number(value: float) -> str:
    """Serialize a JSON number per RFC 8785 Section 3.2.2.3.

    Every JSON number is treated as an IEEE 754 double, so integers are
    converted before formatting.

    Args:
        value: The number to serialize.

    Returns:
        The canonical textual form.

    Raises:
        CanonicalizationError: If the value is NaN, infinite, or an integer
            too large to represent as a double.
    """
    try:
        as_float = float(value)
    except OverflowError as exc:
        raise CanonicalizationError(
            f"integer {value!r} exceeds the IEEE 754 double range and has no "
            f"RFC 8785 number representation"
        ) from exc

    if as_float != as_float:  # noqa: PLR0124 - the standard NaN test
        raise CanonicalizationError("NaN has no RFC 8785 number representation")
    if as_float in (float("inf"), float("-inf")):
        raise CanonicalizationError(
            f"{value!r} is infinite and has no RFC 8785 number representation"
        )

    return _es6_number_to_string(as_float)


def _serialize_string(value: str) -> str:
    """Serialize a JSON string per RFC 8785 Section 3.2.2.2.

    Args:
        value: The string to serialize.

    Returns:
        The quoted, minimally escaped textual form.

    Raises:
        CanonicalizationError: If the string contains an unpaired surrogate.
    """
    _reject_unencodable(value, "string")

    parts = ['"']
    for char in value:
        escape = _SHORT_ESCAPES.get(char)
        if escape is not None:
            parts.append(escape)
        elif ord(char) < _MIN_UNESCAPED_CODE_POINT:
            parts.append(f"\\u{ord(char):04x}")
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def _serialize(value: Any) -> str:
    """Serialize any JSON value into its canonical textual form.

    Args:
        value: A value drawn from the JSON data model.

    Returns:
        The canonical textual form.

    Raises:
        CanonicalizationError: If the value or any value nested inside it has
            no canonical representation.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, (int, float)):
        return _serialize_number(value)
    if isinstance(value, dict):
        return _serialize_object(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise CanonicalizationError(
        f"value of type {type(value).__name__!r} is outside the JSON data model "
        f"and cannot be canonicalized"
    )


def _serialize_object(value: Mapping[str, Any]) -> str:
    """Serialize a JSON object with keys ordered by UTF-16 code unit.

    Args:
        value: The mapping to serialize.

    Returns:
        The canonical textual form.

    Raises:
        CanonicalizationError: If a key is not a string, or any key or nested
            value has no canonical representation.
    """
    for key in value:
        if not isinstance(key, str):
            raise CanonicalizationError(
                f"object key {key!r} is not a string and has no place in the "
                f"JSON data model"
            )

    ordered = sorted(value.items(), key=lambda item: _utf16_sort_key(item[0]))
    body = ",".join(f"{_serialize_string(key)}:{_serialize(item)}" for key, item in ordered)
    return "{" + body + "}"


def canonicalize(value: Any) -> bytes:
    """Canonicalize a JSON value into RFC 8785 bytes.

    Args:
        value: A value drawn from the JSON data model.

    Returns:
        The canonical UTF-8 encoding.

    Raises:
        CanonicalizationError: If the value has no canonical representation.
    """
    return _serialize(value).encode("utf-8")


def signing_payload(card: Mapping[str, Any]) -> dict[str, Any]:
    """Build the Agent Card signing payload by applying the exclusion rule.

    Implements Section 8.4.1 rule 3: the ``signatures`` field is excluded from
    the content being signed, unconditionally, whether or not it is populated.

    Args:
        card: The Agent Card as received.

    Returns:
        A copy of the card with the ``signatures`` field removed.

    Raises:
        CanonicalizationError: If the card is not a JSON object.
    """
    if not isinstance(card, dict):
        raise CanonicalizationError(
            f"Agent Card must be a JSON object, got {type(card).__name__!r}"
        )
    return {key: item for key, item in card.items() if key != SIGNATURES_FIELD}


def canonicalize_agent_card(card: Mapping[str, Any]) -> bytes:
    """Compute the canonical signing payload bytes for an Agent Card.

    Applies Section 8.4.1 rule 3 (exclude ``signatures``) and then rule 2
    (canonicalize per RFC 8785).

    Args:
        card: The Agent Card as received.

    Returns:
        The canonical UTF-8 bytes an implementation must sign.

    Raises:
        CanonicalizationError: If the card has no canonical representation.
    """
    return canonicalize(signing_payload(card))


def assert_signatures_excluded(payload: Mapping[str, Any]) -> None:
    """Check that a prepared signing payload no longer carries ``signatures``.

    Section 8.4.1 rule 3 makes a payload that still carries the field invalid
    signing input, because signing it would create the circular dependency the
    rule exists to prevent.

    Args:
        payload: The signing payload to check.

    Raises:
        CanonicalizationError: If the payload still carries the field.
    """
    if isinstance(payload, dict) and SIGNATURES_FIELD in payload:
        raise CanonicalizationError(
            f"signing payload still carries the {SIGNATURES_FIELD!r} field, which "
            f"specification section 8.4.1 rule 3 requires to be excluded"
        )
