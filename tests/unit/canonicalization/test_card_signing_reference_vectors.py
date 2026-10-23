"""Agent Card signing payload tests driven by the CARD-SIGN reference vectors.

Requirements tested:
    CARD-SIGN-001, CARD-SIGN-002

The fixture ``card_signing_reference_vectors.json`` is a byte-for-byte copy of
``tests/unit/agent_card/card_signing_vectors.json`` from #194 at d366cbc
(sha256 fa1e48dec93d7093798ed37dff0d7096f8f70336046d1ede687b3f4fcd073326).
Canonicalization vectors originated in #194 (AlgoVoi), reused with permission.

Each case pins the RFC 8785 signing payload of a card after the ``signatures``
field is excluded (Section 8.4.1 rules 2 and 3).  The two signing cases also
pin the JWS protected header encoding and the JWS signing input built from
them.  The Ed25519 signature bytes the fixture carries are not checked here:
the TCK depends on no signature library, and the signing input is the part of
the worked example that a canonicalizer decides.
"""

from __future__ import annotations

import base64
import hashlib
import json

from pathlib import Path
from typing import Any

import pytest

from tck.canonicalization.jcs import canonicalize, canonicalize_agent_card


FIXTURE_PATH = Path(__file__).parent / "card_signing_reference_vectors.json"
FIXTURE_SHA256 = "fa1e48dec93d7093798ed37dff0d7096f8f70336046d1ede687b3f4fcd073326"

FIXTURE: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
CANONICALIZATION_CASES: list[dict[str, Any]] = FIXTURE["canonicalization_cases"]
SIGNING_CASES: list[dict[str, Any]] = FIXTURE["signing_cases"]
ALL_CASES = CANONICALIZATION_CASES + SIGNING_CASES


def _b64url(data: bytes) -> str:
    """Encode bytes as unpadded base64url, as JWS compact serialization does."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def test_fixture_is_the_copy_from_194() -> None:
    """CARD-SIGN-001: the fixture is unchanged since it was copied from #194."""
    digest = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256, f"fixture hashes to {digest}, expected {FIXTURE_SHA256}"


def test_fixture_holds_six_canonicalization_and_two_signing_cases() -> None:
    """CARD-SIGN-001: every case in the fixture is collected below."""
    assert (len(CANONICALIZATION_CASES), len(SIGNING_CASES)) == (6, 2)


@pytest.mark.parametrize("case", ALL_CASES, ids=[c["id"] for c in ALL_CASES])
def test_signing_payload_matches(case: dict[str, Any]) -> None:
    """CARD-SIGN-001, CARD-SIGN-002: the canonical signing payload is exact."""
    produced = canonicalize_agent_card(case["agent_card"])
    assert produced == case["expected_jcs_payload"].encode("utf-8")


@pytest.mark.parametrize("case", SIGNING_CASES, ids=[c["id"] for c in SIGNING_CASES])
def test_protected_header_encoding_matches(case: dict[str, Any]) -> None:
    """CARD-SIGN-001: the protected header is the base64url of its canonical form."""
    assert _b64url(canonicalize(case["protected_header"])) == case["expected_protected_b64"]


@pytest.mark.parametrize("case", SIGNING_CASES, ids=[c["id"] for c in SIGNING_CASES])
def test_signing_input_matches(case: dict[str, Any]) -> None:
    """CARD-SIGN-001: the JWS signing input joins header and payload encodings."""
    payload = canonicalize_agent_card(case["agent_card"])
    signing_input = f"{case['expected_protected_b64']}.{_b64url(payload)}"
    assert signing_input == case["expected_signing_input"]
