"""Agent Card signature validation (spec Section 8.4).

Implements the conformance checks behind the ``CARD-SIGN-*`` requirements:

* ``CARD-SIGN-003`` -- the JWS protected header carries non-empty ``alg``
  and ``kid`` values (:func:`check_signature_headers`).
* ``CARD-SIGN-001`` / ``CARD-SIGN-002`` -- the signature verifies against the
  payload canonicalized per Section 8.4.3, proving JCS canonicalization with
  the ``signatures`` field excluded (:func:`verify_card_signatures`).

Verification reproduces the spec's algorithm: exclude ``signatures``, remove
properties holding Protocol Buffer default values, JSON-canonicalize with
RFC 8785, then verify the detached JWS against the resolved public key.

This module requires the ``signing`` optional dependency group
(``jwcrypto`` + ``rfc8785``).
"""

from __future__ import annotations

import base64
import binascii
import copy
import json

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import rfc8785

from jwcrypto import jwk, jws
from jwcrypto.common import JWException

from specification.generated import a2a_pb2


if TYPE_CHECKING:
    from collections.abc import Callable

    from google.protobuf.descriptor import Descriptor, FieldDescriptor


# Protobuf field-type numbers used for default detection (descriptor.FieldDescriptor.TYPE_*).
_TYPE_MESSAGE = 11
_TYPE_STRING = 9
_TYPE_BYTES = 12
_TYPE_BOOL = 8
_TYPE_ENUM = 14

# Sentinel marking a property that must be omitted from the canonical form.
_OMIT = object()


class KeyResolutionError(Exception):
    """The ``jku`` JWKS fetch or parse failed; recorded on the outcome."""


@dataclass
class VerificationOutcome:
    """Result of verifying a card's ``signatures`` array.

    Attributes:
        verified: True if at least one signature verified.
        inconclusive: True if no signature could be checked because no public
            key was resolvable (distinct from a verification failure).
        errors: Human-readable failure or inconclusive reasons.
    """

    verified: bool = False
    inconclusive: bool = False
    errors: list[str] = field(default_factory=list)


def _decode_protected(protected_b64: str) -> dict[str, Any]:
    """Base64url-decode a JWS protected header into a JSON object.

    Raises:
        ValueError: on undecodable base64, non-JSON content, a non-object
            header, or JSON nested too deeply to parse (a hostile ``protected``
            value); callers treat every case as a recorded header error.
    """
    padded = protected_b64 + "=" * (-len(protected_b64) % 4)
    raw = base64.urlsafe_b64decode(padded)
    try:
        header = json.loads(raw)
    except RecursionError as exc:
        raise ValueError("protected header JSON is nested too deeply") from exc
    if not isinstance(header, dict):
        raise ValueError("protected header is not a JSON object")
    return header


def check_signature_headers(card: dict[str, Any]) -> list[str]:
    """Validate JWS protected headers of every signature (CARD-SIGN-003).

    Args:
        card: The Agent Card as a JSON object.

    Returns:
        A list of error strings; empty when every signature's protected header
        declares non-empty ``alg`` and ``kid`` string values.
    """
    if not isinstance(card, dict):
        return ["agent card is not a JSON object"]
    errors: list[str] = []
    signatures = card.get("signatures", [])
    if not isinstance(signatures, list):
        return ["'signatures' is present but is not a JSON array"]
    for index, signature in enumerate(signatures):
        if not isinstance(signature, dict):
            errors.append(f"signatures[{index}]: entry is not a JSON object")
            continue
        protected_b64 = signature.get("protected")
        if not isinstance(protected_b64, str) or not protected_b64:
            errors.append(f"signatures[{index}]: missing required 'protected' header")
            continue
        try:
            header = _decode_protected(protected_b64)
        except (ValueError, binascii.Error, json.JSONDecodeError) as exc:
            errors.append(f"signatures[{index}]: protected header is not valid base64url JSON ({exc})")
            continue
        # Deliberately no algorithm allowlist: Section 8.4.2 names ES256/RS256 as
        # examples, not a closed set, and the requirement only mandates presence.
        if "alg" not in header:
            errors.append(f"signatures[{index}]: protected header missing required 'alg'")
        elif not isinstance(header["alg"], str) or not header["alg"]:
            errors.append(f"signatures[{index}]: 'alg' must be a non-empty string, got {header['alg']!r}")
        if "kid" not in header:
            errors.append(f"signatures[{index}]: protected header missing required 'kid'")
        elif not isinstance(header["kid"], str) or not header["kid"]:
            errors.append(f"signatures[{index}]: 'kid' must be a non-empty string, got {header['kid']!r}")
    return errors


def _field_default(descriptor: FieldDescriptor) -> object:
    """Return the JSON-shaped default value for a singular scalar field."""
    if descriptor.type in (_TYPE_STRING, _TYPE_BYTES):
        return ""
    if descriptor.type == _TYPE_BOOL:
        return False
    if descriptor.type == _TYPE_ENUM:
        return descriptor.enum_type.values[0].name
    return 0


def _is_map_field(descriptor: FieldDescriptor) -> bool:
    """True if the field is a protobuf map (serialized as a JSON object)."""
    return bool(descriptor.type == _TYPE_MESSAGE and descriptor.message_type.GetOptions().map_entry)


def _strip_maybe_message(value: Any, message_type: Descriptor) -> object:
    """Strip a nested message, passing non-object values through untouched.

    A hostile card may put a scalar where a message is expected; leaving it as-is
    lets verification fail rather than raising while canonicalizing.
    """
    if not isinstance(value, dict):
        return value
    return _strip_message(value, message_type)


def _strip_repeated(value: Any, descriptor: FieldDescriptor) -> object:
    if not isinstance(value, list) or not value:
        return _OMIT
    if descriptor.type == _TYPE_MESSAGE:
        return [_strip_maybe_message(item, descriptor.message_type) for item in value]
    return value


def _strip_map(value: Any, descriptor: FieldDescriptor) -> object:
    if not isinstance(value, dict) or not value:
        return _OMIT
    value_field = descriptor.message_type.fields_by_name["value"]
    if value_field.type == _TYPE_MESSAGE:
        return {k: _strip_maybe_message(v, value_field.message_type) for k, v in value.items()}
    return value


def _strip_field(value: Any, descriptor: FieldDescriptor) -> object:
    """Apply default-value removal to one field's value, or return ``_OMIT``."""
    if _is_map_field(descriptor):
        return _strip_map(value, descriptor)
    if descriptor.is_repeated:
        return _strip_repeated(value, descriptor)
    if descriptor.type == _TYPE_MESSAGE:
        if not isinstance(value, dict):
            return value
        stripped = _strip_message(value, descriptor.message_type)
        if not stripped and not descriptor.has_presence:
            return _OMIT
        return stripped
    if not descriptor.has_presence and value == _field_default(descriptor):
        return _OMIT
    return value


def _strip_message(value: dict[str, Any], descriptor: Descriptor) -> dict[str, Any]:
    """Recursively remove default-valued properties from a message object.

    Unknown keys (absent from the descriptor) are preserved so that forward-
    compatible cards are not silently mutated; an unsigned extra field simply
    causes verification to fail, which is the correct conformance outcome.

    Recursion is bounded by the (non-recursive) ``AgentCard`` schema, so hostile
    nesting lands in unknown keys instead -- guarded by the ``RecursionError``
    handling around :func:`canonicalize_for_signing`'s callers.
    """
    by_json = {f.json_name: f for f in descriptor.fields}
    by_name = {f.name: f for f in descriptor.fields}
    result: dict[str, Any] = {}
    for key, raw in value.items():
        descriptor_field = by_json.get(key) or by_name.get(key)
        if descriptor_field is None:
            result[key] = raw
            continue
        stripped = _strip_field(raw, descriptor_field)
        if stripped is not _OMIT:
            result[key] = stripped
    return result


def canonicalize_for_signing(card: dict[str, Any], *, strip_defaults: bool = True) -> bytes:
    """Produce the JCS canonical signing payload for a card (Section 8.4.1).

    Excludes the ``signatures`` field, optionally removes Protocol Buffer
    default-valued properties, then canonicalizes with RFC 8785.

    Args:
        card: The Agent Card as a JSON object.
        strip_defaults: When True, remove default-valued properties using the
            ``AgentCard`` protobuf descriptors before canonicalization.

    Returns:
        The canonical payload bytes that a conformant signature is computed over.
    """
    payload = copy.deepcopy(card)
    payload.pop("signatures", None)
    if strip_defaults:
        payload = _strip_message(payload, a2a_pb2.AgentCard.DESCRIPTOR)
    return rfc8785.dumps(payload)


def _resolve_key(
    header: dict[str, Any],
    trusted_keys: dict[str, Any] | None,
    fetch_jwks: Callable[[str], dict[str, Any]] | None,
) -> jwk.JWK | None:
    """Resolve the verification key from a trusted store or the ``jku`` JWKS."""
    kid = header.get("kid")
    if trusted_keys and kid in trusted_keys:
        return _as_jwk(trusted_keys[kid])
    jku = header.get("jku")
    if jku and fetch_jwks is not None:
        try:
            keyset = jwk.JWKSet.from_json(json.dumps(fetch_jwks(jku)))
            key = keyset.get_key(kid) if kid else None
        except Exception as exc:  # fetch_jwks is caller-supplied and may raise anything (network, parsing)
            raise KeyResolutionError(f"jku fetch/parse failed ({exc})") from exc
        if key is not None:
            return key
    return None


def _resolve_key_safe(
    header: dict[str, Any],
    trusted_keys: dict[str, Any] | None,
    fetch_jwks: Callable[[str], dict[str, Any]] | None,
) -> tuple[jwk.JWK | None, str | None]:
    """Resolve a key, converting any resolution failure into an error string."""
    try:
        return _resolve_key(header, trusted_keys, fetch_jwks), None
    except (KeyResolutionError, JWException, ValueError, TypeError, KeyError, RecursionError) as exc:
        return None, f"key resolution failed ({exc})"


def _as_jwk(candidate: Any) -> jwk.JWK:
    if isinstance(candidate, jwk.JWK):
        return candidate
    return jwk.JWK.from_json(json.dumps(candidate))


def _verify_one(signature: dict[str, Any], key: jwk.JWK, payload: bytes) -> bool:
    """True if the signature verifies against the canonical payload.

    Any malformed attacker-controlled JWS (bad ``signature`` value, undeserializable
    token) is treated as a verification failure rather than propagating.
    """
    serialized = json.dumps({"protected": signature["protected"], "signature": signature["signature"]})
    token = jws.JWS()
    try:
        token.deserialize(serialized)
        token.verify(key, detached_payload=payload)
    except (JWException, ValueError, TypeError):
        return False
    return True


def _entry_error(signature: Any, index: int) -> str | None:
    """Return an error string if a ``signatures`` entry is structurally invalid."""
    if not isinstance(signature, dict):
        return f"signatures[{index}]: entry is not a JSON object"
    for member in ("protected", "signature"):
        value = signature.get(member)
        if not isinstance(value, str) or not value:
            return f"signatures[{index}]: '{member}' must be a non-empty string"
    return None


def verify_card_signatures(
    card: dict[str, Any],
    *,
    trusted_keys: dict[str, Any] | None = None,
    fetch_jwks: Callable[[str], dict[str, Any]] | None = None,
) -> VerificationOutcome:
    """Verify a card's signatures per Section 8.4.3 (CARD-SIGN-001/002).

    A signature is accepted only when it verifies against the spec's single
    canonical payload: ``signatures`` excluded and proto-default properties
    removed (Section 8.4.2 step 1). Accepting a non-canonical form would let a
    non-conformant signer pass, so verification is intentionally strict; a card
    that a conformant signer produced always matches this form. (The descriptor
    strip cannot model the spec's ``REQUIRED``-field carve-out, so an unusual
    card could yield a false *negative* -- the safe direction for a kit.)

    Args:
        card: The Agent Card as a JSON object.
        trusted_keys: Optional mapping of ``kid`` to a JWK (dict or
            :class:`jwcrypto.jwk.JWK`); consulted before any network lookup.
        fetch_jwks: Optional callable mapping a ``jku`` URL to a JWKS object.
            The injection point for the network boundary; ``None`` (the default)
            keeps verification fully offline. A caller that supplies one is
            responsible for its own SSRF guards, since ``jku`` is attacker-
            controlled card content.

    Returns:
        A :class:`VerificationOutcome`. ``inconclusive`` is set only when no
        signature could be checked because no key was resolvable.
    """
    if not isinstance(card, dict):
        return VerificationOutcome(errors=["agent card is not a JSON object"])
    signatures = card.get("signatures", [])
    if not isinstance(signatures, list):
        return VerificationOutcome(errors=["'signatures' is present but is not a JSON array"])
    try:
        payload = canonicalize_for_signing(card, strip_defaults=True)
    except (TypeError, ValueError, RecursionError) as exc:
        return VerificationOutcome(errors=[f"card canonicalization failed ({exc})"])
    outcome = VerificationOutcome()
    checked_any = False
    for index, signature in enumerate(signatures):
        entry_error = _entry_error(signature, index)
        if entry_error is not None:
            outcome.errors.append(entry_error)
            continue
        try:
            header = _decode_protected(signature["protected"])
        except (ValueError, binascii.Error, json.JSONDecodeError) as exc:
            outcome.errors.append(f"signatures[{index}]: undecodable protected header ({exc})")
            continue
        key, resolve_error = _resolve_key_safe(header, trusted_keys, fetch_jwks)
        if resolve_error is not None:
            outcome.errors.append(f"signatures[{index}]: {resolve_error}")
            continue
        if key is None:
            outcome.errors.append(f"signatures[{index}]: no verification key resolvable for kid={header.get('kid')!r}")
            continue
        checked_any = True
        if _verify_one(signature, key, payload):
            outcome.verified = True
            return outcome
        outcome.errors.append(f"signatures[{index}]: signature did not verify")
    if not checked_any and not outcome.verified:
        outcome.inconclusive = True
    return outcome
