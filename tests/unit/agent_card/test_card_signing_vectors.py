"""Reference canonicalization and signing vectors for AgentCard signing (CARD-SIGN-001/002).

These cases do not exercise a SUT and do not change the NOT_AUTOMATABLE status of the
CARD-SIGN requirements. They give the kit fixed, known-good bytes for the two halves of
spec section 8.4:

  8.4.1 Canonicalization  the RFC 8785 (JCS) signing payload, with the signatures field excluded.
  8.4.2 Signature Format  the full JWS worked example: protected header, JWS signing input, and
                          an EdDSA signature over that input (spec 8.4.3 verification).

The canonicalization cases include three that a canonicalizer implemented as
`json.dumps(card, sort_keys=True, separators=(",", ":"))` reproduces, and three that it does
not (number serialization, non-ASCII string escaping, and UTF-16 key ordering), so the vectors
actually discriminate a conformant RFC 8785 implementation from a naive one.

The signing key is a fixed, throwaway Ed25519 test key published in the vectors file. EdDSA is
deterministic (RFC 8032), so the committed signature is byte-reproducible from the private key,
which the crypto-guarded assertions below check.

Vectors come from card_ref (github.com/chopmob-cloud/AlgoVoi-A2A-Card) and the
algovoi-jcs-conformance-vectors corpus. Apache-2.0.
"""
from __future__ import annotations

import base64
import json

from pathlib import Path

import pytest


rfc8785 = pytest.importorskip("rfc8785")

_VECTORS = json.loads(Path(__file__).with_name("card_signing_vectors.json").read_text(encoding="utf-8"))


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _jcs_signing_payload(card: dict) -> bytes:
    # spec 8.4.1 rule 3: exclude the signatures field, then RFC 8785 (JCS).
    prepared = {k: v for k, v in card.items() if k != "signatures"}
    return rfc8785.dumps(prepared)


@pytest.mark.parametrize("case", _VECTORS["canonicalization_cases"], ids=lambda c: c["id"])
def test_canonical_signing_payload(case: dict) -> None:
    """The JCS signing payload equals the expected canonical bytes, signatures excluded."""
    payload = _jcs_signing_payload(case["agent_card"]).decode("utf-8")
    assert payload == case["expected_jcs_payload"], (
        f"{case['id']} ({case['requirement']}): canonical signing payload mismatch"
    )


@pytest.mark.parametrize(
    "case",
    [c for c in _VECTORS["canonicalization_cases"] if c["id"].startswith("cardsign-jcs")],
    ids=lambda c: c["id"],
)
def test_discriminating_cases_reject_naive_canonicalizer(case: dict) -> None:
    """Each cardsign-jcs case must NOT be reproduced by naive json.dumps(sort_keys)."""
    prepared = {k: v for k, v in case["agent_card"].items() if k != "signatures"}
    naive = json.dumps(prepared, sort_keys=True, separators=(",", ":"))
    assert naive != case["expected_jcs_payload"], (
        f"{case['id']}: expected to distinguish JCS from a naive canonicalizer, but they match"
    )


@pytest.mark.parametrize("case", _VECTORS["signing_cases"], ids=lambda c: c["id"])
def test_jws_signing_input(case: dict) -> None:
    """Reconstruct the JWS signing input from the card and assert it matches the vector.

    Crypto-free: exercises canonicalization (8.4.1) and JWS signing-input assembly (8.4.2
    step 3) with only rfc8785 and the standard library, so it runs under CI unconditionally.
    """
    payload = _jcs_signing_payload(case["agent_card"])
    assert payload.decode("utf-8") == case["expected_jcs_payload"]

    protected_b64 = _b64url_encode(rfc8785.dumps(case["protected_header"]))
    assert protected_b64 == case["expected_protected_b64"], f"{case['id']}: protected header mismatch"

    signing_input = protected_b64 + "." + _b64url_encode(payload)
    assert signing_input == case["expected_signing_input"], f"{case['id']}: JWS signing input mismatch"


@pytest.mark.parametrize("case", _VECTORS["signing_cases"], ids=lambda c: c["id"])
def test_jws_signature_verifies_and_is_reproducible(case: dict) -> None:
    """Verify the EdDSA signature and reproduce it from the private key.

    Guarded on `cryptography` so the kit takes no crypto dependency; skips where it is absent.
    """
    ed = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    from cryptography.exceptions import InvalidSignature

    signing_input = case["expected_signing_input"].encode("ascii")
    signature = _b64url_decode(case["signature"])

    public_jwk = _VECTORS["public_jwk"]
    public_key = ed.Ed25519PublicKey.from_public_bytes(_b64url_decode(public_jwk["x"]))
    try:
        public_key.verify(signature, signing_input)
    except InvalidSignature:  # pragma: no cover - a failure is the assertion
        pytest.fail(f"{case['id']}: published signature does not verify against public_jwk")

    private_jwk = _VECTORS["private_jwk"]
    private_key = ed.Ed25519PrivateKey.from_private_bytes(_b64url_decode(private_jwk["d"]))
    assert private_key.sign(signing_input) == signature, (
        f"{case['id']}: EdDSA signature is not reproducible from the private key"
    )
