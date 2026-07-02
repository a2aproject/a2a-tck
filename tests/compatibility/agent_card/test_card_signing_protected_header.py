"""Reference tests for AgentCard signing protected header validation (CARD-SIGN-003).

CARD-SIGN-003 (spec §8.4.2): The JWS protected header MUST include alg (algorithm)
and kid (key ID) parameters.

These are structural, offline tests: they decode each signature's base64url-encoded
protected header and verify alg and kid are present, non-empty strings. No SUT is
required — the test operates on static vectors, following the same reference-vector
pattern as test_card_signing_canonicalization.py.

Vectors are derived from standard JWS examples. Apache-2.0.
"""
from __future__ import annotations

import base64
import json

from pathlib import Path

import pytest


_VECTORS = json.loads(
    (Path(__file__).with_name("card_signing_protected_header_vectors.json")).read_text(
        encoding="utf-8"
    )
)

# Known JWS algorithm names from RFC 7518 §3.1.
# The A2A spec §8.4.2 requires alg to be present; these are the standard values.
_KNOWN_JWS_ALGORITHMS: frozenset[str] = frozenset(
    {
        # ECDSA
        "ES256",
        "ES384",
        "ES512",
        # RSA
        "RS256",
        "RS384",
        "RS512",
        # RSA-PSS
        "PS256",
        "PS384",
        "PS512",
        # EdDSA
        "EdDSA",
    }
)


def _decode_protected_header(protected: str) -> dict:
    """Base64url-decode a JWS protected header to JSON.

    Handles both padded and unpadded base64url per RFC 7515 §2.
    """
    # Add padding if missing (base64url may omit '=' padding)
    missing_padding = len(protected) % 4
    if missing_padding:
        protected += "=" * (4 - missing_padding)
    raw = base64.urlsafe_b64decode(protected)
    return json.loads(raw)


def _validate_protected_header(
    case_id: str, header: dict
) -> list[str]:
    """Validate that a decoded JWS protected header satisfies CARD-SIGN-003.

    Returns a list of error messages (empty list = valid).
    """
    errors: list[str] = []

    alg = header.get("alg")
    if not alg or not isinstance(alg, str) or not alg.strip():
        errors.append(f"{case_id}: alg missing or empty")

    kid = header.get("kid")
    if not kid or not isinstance(kid, str) or not kid.strip():
        errors.append(f"{case_id}: kid missing or empty")

    return errors


@pytest.mark.parametrize("case", _VECTORS["cases"], ids=lambda c: c["id"])
def test_protected_header_has_alg_and_kid(case: dict) -> None:
    """CARD-SIGN-003: JWS protected header MUST include alg and kid."""
    card = case["agent_card"]
    signatures = card.get("signatures", [])

    if not signatures:
        pytest.skip(f"{case['id']}: no signatures in card — signing is MAY (§8.4)")

    decode_errors: list[str] = []
    validation_errors: list[str] = []

    for i, sig in enumerate(signatures):
        protected = sig.get("protected", "")

        # Decode
        try:
            header = _decode_protected_header(protected)
        except Exception as exc:
            decode_errors.append(
                f"{case['id']}: signature[{i}] protected header decode failed: {exc}"
            )
            continue

        # Validate
        errs = _validate_protected_header(case["id"], header)
        if errs:
            validation_errors.extend(errs)

    if case["expected_valid"]:
        all_errors = decode_errors + validation_errors
        assert not all_errors, "; ".join(all_errors)
    else:
        assert (
            validation_errors or decode_errors
        ), f"{case['id']}: expected validation failure but got none"
        if "expected_error" in case:
            error_text = "; ".join(validation_errors + decode_errors).lower()
            assert case["expected_error"].lower() in error_text, (
                f"{case['id']}: expected error containing '{case['expected_error']}', "
                f"got: {'; '.join(validation_errors + decode_errors)}"
            )


@pytest.mark.parametrize("case", _VECTORS["cases"], ids=lambda c: c["id"])
def test_protected_header_alg_is_known_jws_algorithm(case: dict) -> None:
    """CARD-SIGN-003 (SHOULD): alg SHOULD be a known JWS algorithm from RFC 7518.

    This is a SHOULD-level advisory check, not a MUST. A non-standard alg
    produces a warning-level failure rather than a hard assertion.
    """
    signatures = case["agent_card"].get("signatures", [])
    if not signatures:
        pytest.skip(f"{case['id']}: no signatures in card")

    for i, sig in enumerate(signatures):
        protected = sig.get("protected", "")
        try:
            header = _decode_protected_header(protected)
        except Exception:
            continue  # decode failure handled by test_protected_header_has_alg_and_kid

        alg = header.get("alg", "")
        if alg and alg not in _KNOWN_JWS_ALGORITHMS:
            pytest.fail(
                f"{case['id']}: signature[{i}] alg='{alg}' is not a known "
                f"JWS algorithm from RFC 7518 §3.1. Known: "
                f"{sorted(_KNOWN_JWS_ALGORITHMS)}"
            )
