"""Tests for the Agent Card signature validator (CARD-SIGN-*)."""

from __future__ import annotations

import json

from typing import Any

import pytest


pytest.importorskip("jwcrypto")
pytest.importorskip("rfc8785")

from jwcrypto import jwk, jws

from tck.validators.card_signature import (
    canonicalize_for_signing,
    check_signature_headers,
    verify_card_signatures,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_card() -> dict[str, Any]:
    """Return a minimal spec-shaped Agent Card with a default-valued field."""
    return {
        "name": "GeoRoute",
        "description": "Route planner",
        "version": "1.2.0",
        "supportedInterfaces": [{"url": "https://a.example/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
        "capabilities": {"streaming": False, "pushNotifications": True},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [],
    }


def _sign(card: dict[str, Any], key: jwk.JWK, kid: str, *, jku: str | None = None) -> dict[str, Any]:
    """Return a spec-conformant signed copy of ``card`` (spec Section 8.4.2)."""
    payload = canonicalize_for_signing(card, strip_defaults=True)
    header: dict[str, Any] = {"alg": "ES256", "typ": "JOSE", "kid": kid}
    if jku is not None:
        header["jku"] = jku
    token = jws.JWS(payload)
    token.add_signature(key, alg="ES256", protected=json.dumps(header))
    flat = json.loads(token.serialize())
    return {**card, "signatures": [{"protected": flat["protected"], "signature": flat["signature"]}]}


def _sign_with_header(card: dict[str, Any], key: jwk.JWK, header: dict[str, Any]) -> dict[str, Any]:
    """Sign ``card`` with an arbitrary protected ``header`` for negative tests."""
    payload = canonicalize_for_signing(card, strip_defaults=True)
    token = jws.JWS(payload)
    token.add_signature(key, alg="ES256", protected=json.dumps(header))
    flat = json.loads(token.serialize())
    return {**card, "signatures": [{"protected": flat["protected"], "signature": flat["signature"]}]}


@pytest.fixture
def key() -> jwk.JWK:
    """Generate an ES256 signing key with a fixed key id."""
    return jwk.JWK.generate(kty="EC", crv="P-256", kid="key-1")


@pytest.fixture
def public_jwks(key: jwk.JWK) -> dict[str, Any]:
    """Return a JWKS document carrying the public half of ``key``."""
    return {"keys": [key.export_public(as_dict=True)]}


# ---------------------------------------------------------------------------
# CARD-SIGN-003 -- protected header
# ---------------------------------------------------------------------------


class TestSignatureHeaders:
    """CARD-SIGN-003: the JWS protected header carries alg and kid."""

    def test_valid_header_passes(self, key: jwk.JWK) -> None:
        """A conformant signature reports no header errors."""
        signed = _sign(_base_card(), key, "key-1")
        assert check_signature_headers(signed) == []

    def test_missing_kid_reported(self, key: jwk.JWK) -> None:
        """A protected header without kid is flagged."""
        signed = _sign_with_header(_base_card(), key, {"alg": "ES256", "typ": "JOSE"})
        assert any("kid" in error for error in check_signature_headers(signed))

    def test_missing_alg_reported(self, key: jwk.JWK) -> None:
        """A protected header without alg is flagged."""
        signed = _sign_with_header(_base_card(), key, {"typ": "JOSE", "kid": "key-1"})
        assert any("alg" in error for error in check_signature_headers(signed))

    def test_non_string_alg_reported(self) -> None:
        """A non-string alg value is flagged as malformed."""
        import base64

        protected = base64.urlsafe_b64encode(json.dumps({"alg": 123, "kid": "key-1"}).encode()).decode().rstrip("=")
        card = {**_base_card(), "signatures": [{"protected": protected, "signature": "AA"}]}
        assert any("non-empty string" in error for error in check_signature_headers(card))

    def test_empty_kid_reported(self) -> None:
        """An empty kid value is flagged as malformed."""
        import base64

        protected = base64.urlsafe_b64encode(json.dumps({"alg": "ES256", "kid": ""}).encode()).decode().rstrip("=")
        card = {**_base_card(), "signatures": [{"protected": protected, "signature": "AA"}]}
        assert any("non-empty string" in error for error in check_signature_headers(card))

    def test_unlisted_algorithm_accepted(self) -> None:
        """An algorithm outside the spec's examples (e.g. EdDSA) is not flagged."""
        import base64

        protected = base64.urlsafe_b64encode(json.dumps({"alg": "EdDSA", "kid": "key-1"}).encode()).decode().rstrip("=")
        card = {**_base_card(), "signatures": [{"protected": protected, "signature": "AA"}]}
        assert check_signature_headers(card) == []

    def test_unsigned_card_has_no_header_errors(self) -> None:
        """An unsigned card produces no header errors (nothing to check)."""
        assert check_signature_headers(_base_card()) == []


# ---------------------------------------------------------------------------
# CARD-SIGN-001 / 002 -- verification
# ---------------------------------------------------------------------------


class TestVerification:
    """CARD-SIGN-001/002: signature verifies over the canonical payload."""

    def test_verifies_with_trusted_key(self, key: jwk.JWK) -> None:
        """A trusted-key lookup verifies a conformant signature."""
        signed = _sign(_base_card(), key, "key-1")
        outcome = verify_card_signatures(signed, trusted_keys={"key-1": key})
        assert outcome.verified
        assert not outcome.inconclusive

    def test_verifies_via_jku_fetch(self, key: jwk.JWK, public_jwks: dict[str, Any]) -> None:
        """A jku JWKS fetch resolves the key and verifies the signature."""
        signed = _sign(_base_card(), key, "key-1", jku="https://a.example/jwks.json")
        outcome = verify_card_signatures(signed, fetch_jwks=lambda _url: public_jwks)
        assert outcome.verified

    def test_verifies_card_with_explicit_default_field(self, key: jwk.JWK) -> None:
        """Verification succeeds even when the card serializes default values."""
        signed = _sign(_base_card(), key, "key-1")
        outcome = verify_card_signatures(signed, trusted_keys={"key-1": key})
        assert outcome.verified

    def test_tampered_card_fails(self, key: jwk.JWK) -> None:
        """Mutating a signed field fails verification (not inconclusive)."""
        signed = _sign(_base_card(), key, "key-1")
        signed["name"] = "Tampered"
        outcome = verify_card_signatures(signed, trusted_keys={"key-1": key})
        assert not outcome.verified
        assert not outcome.inconclusive
        assert any("did not verify" in error for error in outcome.errors)

    def test_signatures_not_excluded_fails(self, key: jwk.JWK) -> None:
        """A signature computed without excluding signatures fails (CARD-SIGN-002)."""
        import rfc8785

        polluted = {**_base_card(), "signatures": [{"protected": "x", "signature": "y"}]}
        payload = rfc8785.dumps(polluted)
        token = jws.JWS(payload)
        token.add_signature(key, alg="ES256", protected=json.dumps({"alg": "ES256", "typ": "JOSE", "kid": "key-1"}))
        flat = json.loads(token.serialize())
        signed = {**_base_card(), "signatures": [{"protected": flat["protected"], "signature": flat["signature"]}]}
        outcome = verify_card_signatures(signed, trusted_keys={"key-1": key})
        assert not outcome.verified

    def test_wrong_key_fails(self, key: jwk.JWK) -> None:
        """A different key under the same kid fails verification."""
        signed = _sign(_base_card(), key, "key-1")
        other = jwk.JWK.generate(kty="EC", crv="P-256", kid="key-1")
        outcome = verify_card_signatures(signed, trusted_keys={"key-1": other})
        assert not outcome.verified

    def test_no_key_is_inconclusive(self, key: jwk.JWK) -> None:
        """A signed card with no resolvable key is inconclusive, not failed."""
        signed = _sign(_base_card(), key, "key-1")
        outcome = verify_card_signatures(signed)
        assert not outcome.verified
        assert outcome.inconclusive

    def test_unsigned_card_is_inconclusive(self) -> None:
        """An unsigned card has nothing to verify and is inconclusive."""
        outcome = verify_card_signatures(_base_card())
        assert not outcome.verified
        assert outcome.inconclusive


# ---------------------------------------------------------------------------
# Hostile input -- a conformance kit fetches arbitrary third-party cards, so
# malformed structures must produce recorded errors, never exceptions.
# ---------------------------------------------------------------------------


class TestHostileInput:
    """Malformed cards report failures rather than crashing the run."""

    def test_signatures_not_a_list_headers(self) -> None:
        """A non-array signatures value is reported, not iterated blindly."""
        card = {**_base_card(), "signatures": 5}
        errors = check_signature_headers(card)
        assert errors and "not a JSON array" in errors[0]

    def test_signatures_not_a_list_verify(self) -> None:
        """Verification of a non-array signatures value fails cleanly."""
        card = {**_base_card(), "signatures": 5}
        outcome = verify_card_signatures(card)
        assert not outcome.verified
        assert any("not a JSON array" in error for error in outcome.errors)

    def test_non_dict_entry_headers(self) -> None:
        """Non-object signature entries are each flagged, not dereferenced."""
        card = {**_base_card(), "signatures": ["not-an-object", 123]}
        errors = check_signature_headers(card)
        assert errors == [
            "signatures[0]: entry is not a JSON object",
            "signatures[1]: entry is not a JSON object",
        ]

    def test_non_dict_entry_verify(self) -> None:
        """A non-object signature entry fails verification without raising."""
        card = {**_base_card(), "signatures": [123]}
        outcome = verify_card_signatures(card)
        assert not outcome.verified
        assert any("not a JSON object" in error for error in outcome.errors)

    def test_non_string_signature_member(self) -> None:
        """A non-string 'signature' member is flagged as malformed."""
        card = {**_base_card(), "signatures": [{"protected": "abc", "signature": 42}]}
        outcome = verify_card_signatures(card)
        assert not outcome.verified
        assert any("non-empty string" in error for error in outcome.errors)

    def test_undeserializable_signature_value(self, key: jwk.JWK) -> None:
        """A garbage signature value fails verification without raising."""
        signed = _sign(_base_card(), key, "key-1")
        signed["signatures"][0]["signature"] = "!!!not-base64!!!"
        outcome = verify_card_signatures(signed, trusted_keys={"key-1": key})
        assert not outcome.verified
        assert any("did not verify" in error for error in outcome.errors)

    def test_non_dict_card_root_headers(self) -> None:
        """A card root that is not a JSON object is reported, not dereferenced."""
        for root in ([], "err", 123, None):
            errors = check_signature_headers(root)  # type: ignore[arg-type]
            assert errors == ["agent card is not a JSON object"]

    def test_non_dict_card_root_verify(self) -> None:
        """Verifying a non-object card root fails cleanly."""
        for root in ([], "err", 123, None):
            outcome = verify_card_signatures(root)  # type: ignore[arg-type]
            assert not outcome.verified
            assert outcome.errors == ["agent card is not a JSON object"]

    def test_repeated_message_field_with_scalar_items(self, key: jwk.JWK) -> None:
        """A repeated-message field holding scalars canonicalizes without raising."""
        card = {**_base_card(), "skills": ["not-an-object"], "signatures": [{"protected": "a", "signature": "b"}]}
        outcome = verify_card_signatures(card, trusted_keys={"key-1": key})
        assert not outcome.verified

    def test_map_field_with_scalar_value(self, key: jwk.JWK) -> None:
        """A map<string,message> field holding a scalar value does not raise."""
        card = {
            **_base_card(),
            "securitySchemes": {"scheme": "not-an-object"},
            "signatures": [{"protected": "a", "signature": "b"}],
        }
        outcome = verify_card_signatures(card, trusted_keys={"key-1": key})
        assert not outcome.verified

    def test_deeply_nested_protected_header_headers(self) -> None:
        """A deeply-nested JSON protected header is reported, not a stack overflow."""
        import base64

        nested = ("[" * 20000 + "]" * 20000).encode()
        protected = base64.urlsafe_b64encode(nested).decode().rstrip("=")
        card = {**_base_card(), "signatures": [{"protected": protected, "signature": "AA"}]}
        errors = check_signature_headers(card)
        assert any("nested too deeply" in error for error in errors)

    def test_deeply_nested_protected_header_verify(self, key: jwk.JWK) -> None:
        """Verification of a deeply-nested protected header fails without raising."""
        import base64

        nested = ("[" * 20000 + "]" * 20000).encode()
        protected = base64.urlsafe_b64encode(nested).decode().rstrip("=")
        card = {**_base_card(), "signatures": [{"protected": protected, "signature": "AA"}]}
        outcome = verify_card_signatures(card, trusted_keys={"key-1": key})
        assert not outcome.verified
        assert any("nested too deeply" in error for error in outcome.errors)

    def test_deeply_nested_card_reports_error(self, key: jwk.JWK) -> None:
        """A pathologically nested card is rejected, not a stack overflow."""
        deep: dict[str, Any] = {}
        cursor = deep
        for _ in range(5000):
            cursor["ext"] = {}
            cursor = cursor["ext"]
        card = {**_base_card(), "x-deep": deep, "signatures": [{"protected": "abc", "signature": "def"}]}
        outcome = verify_card_signatures(card, trusted_keys={"key-1": key})
        assert not outcome.verified
        assert any("canonicalization failed" in error for error in outcome.errors)


# ---------------------------------------------------------------------------
# Canonicalization
# ---------------------------------------------------------------------------


class TestCanonicalization:
    """canonicalize_for_signing reproduces the spec's signing payload."""

    def test_excludes_signatures_field(self, key: jwk.JWK) -> None:
        """The signatures field is excluded from the canonical payload."""
        signed = _sign(_base_card(), key, "key-1")
        assert b"signatures" not in canonicalize_for_signing(signed, strip_defaults=True)

    def test_strips_empty_repeated_field(self) -> None:
        """An empty repeated field is removed; a non-empty one is retained."""
        canonical = canonicalize_for_signing(_base_card(), strip_defaults=True)
        assert b"skills" not in canonical
        assert b"supportedInterfaces" in canonical

    def test_retains_explicit_presence_default(self) -> None:
        """A proto3 optional field set to its default is retained."""
        assert b"streaming" in canonicalize_for_signing(_base_card(), strip_defaults=True)

    def test_preserves_unknown_keys(self) -> None:
        """Keys absent from the descriptor are preserved, not dropped."""
        card = {**_base_card(), "x-vendor-extension": {"foo": "bar"}}
        assert b"x-vendor-extension" in canonicalize_for_signing(card, strip_defaults=True)
