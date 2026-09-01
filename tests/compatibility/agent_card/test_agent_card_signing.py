"""Agent Card signing conformance tests against a live SUT.

Validates the Section 8.4.1 canonicalization rules against the Agent Card a
server actually serves.

Requirements tested:
    CARD-SIGN-001, CARD-SIGN-002

Signing is optional for an A2A server (Section 8.4), so these tests skip when
the served card carries no ``signatures`` array.  When it does, the card is
held to the two rules that are decidable from the card alone:

* CARD-SIGN-001 -- the signing payload must have an RFC 8785 canonical form at
  all.  A card carrying an unpaired surrogate, a non-finite number, or a value
  outside the JSON data model cannot have been canonicalized per RFC 8785, so
  whatever the server signed was not the canonical form of this card.
* CARD-SIGN-002 -- the payload that gets signed must not carry the
  ``signatures`` field, and the canonical bytes must be reachable while the
  served card still carries it.

Both checks are necessary conditions rather than proof of a correct signature.
Confirming that the server signed *these* bytes means verifying the JWS, which
needs a signature-verification dependency the TCK does not currently take; the
byte-exact half of both requirements is carried by the a2a-jcs-v01 conformance
corpus in ``tests/unit/canonicalization/test_jcs_vectors.py`` instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.canonicalization.jcs import (
    SIGNATURES_FIELD,
    CanonicalizationError,
    assert_signatures_excluded,
    canonicalize_agent_card,
    signing_payload,
)
from tck.requirements.registry import get_requirement_by_id
from tests.compatibility.markers import core, must


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CARD_SIGN_001 = get_requirement_by_id("CARD-SIGN-001")
CARD_SIGN_002 = get_requirement_by_id("CARD-SIGN-002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fail_msg(req: RequirementSpec, detail: str) -> str:
    return (
        f"{req.id} [{req.title}]: {detail} (see {req.spec_url})"
    )


def _record(
    collector: Any,
    req: RequirementSpec,
    passed: bool,
    errors: list[str] | None = None,
) -> None:
    collector.record(
        requirement_id=req.id,
        transport="agent_card",
        level=req.level.value,
        passed=passed,
        errors=errors or [],
    )


def _require_signatures(card: dict[str, Any]) -> list[Any]:
    """Return the card's signatures, or skip when the server does not sign.

    Args:
        card: The served Agent Card.

    Returns:
        The non-empty ``signatures`` array.

    Raises:
        pytest.skip: If the card carries no signatures, since Section 8.4
            makes signing optional.
    """
    signatures: list[Any] = card.get(SIGNATURES_FIELD) or []
    if not signatures:
        pytest.skip(
            "Agent Card carries no signatures; Section 8.4 makes Agent Card "
            "signing optional, so the Section 8.4.1 rules do not apply"
        )
    return signatures


# ---------------------------------------------------------------------------
# Canonicalization (CARD-SIGN-001)
# ---------------------------------------------------------------------------


@must
@core
class TestAgentCardCanonicalization:
    """CARD-SIGN-001: Agent Card canonicalized with JCS before signing."""

    def test_signing_payload_has_a_canonical_form(
        self,
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """CARD-SIGN-001: the served card's signing payload canonicalizes per RFC 8785."""
        req = CARD_SIGN_001
        _require_signatures(agent_card)

        errors: list[str] = []
        try:
            canonical = canonicalize_agent_card(agent_card)
        except CanonicalizationError as exc:
            canonical = b""
            errors.append(
                f"the served Agent Card has no RFC 8785 canonical form, so it "
                f"cannot have been canonicalized before signing: {exc}"
            )

        valid = not errors
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])
        assert canonical, _fail_msg(req, "canonicalization produced no bytes")

    def test_canonicalization_is_stable(
        self,
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """CARD-SIGN-001: canonicalizing the served card twice yields identical bytes.

        RFC 8785 exists to make one document produce one byte string.  A card
        whose canonical form varies between runs cannot carry a signature that
        verifies reliably, whatever the signature itself contains.
        """
        req = CARD_SIGN_001
        _require_signatures(agent_card)

        first = canonicalize_agent_card(agent_card)
        second = canonicalize_agent_card(agent_card)

        valid = first == second
        errors = (
            []
            if valid
            else [f"canonicalization is not deterministic: {first!r} then {second!r}"]
        )
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])


# ---------------------------------------------------------------------------
# Signatures exclusion (CARD-SIGN-002)
# ---------------------------------------------------------------------------


@must
@core
class TestAgentCardSignaturesExclusion:
    """CARD-SIGN-002: Signatures field excluded from signed content."""

    def test_signing_payload_excludes_signatures(
        self,
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """CARD-SIGN-002: the signing payload drops the signatures field."""
        req = CARD_SIGN_002
        _require_signatures(agent_card)

        payload = signing_payload(agent_card)
        errors: list[str] = []
        try:
            assert_signatures_excluded(payload)
        except CanonicalizationError as exc:
            errors.append(str(exc))

        valid = not errors
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])

    def test_canonical_bytes_omit_the_signatures_key(
        self,
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """CARD-SIGN-002: the canonical signing bytes contain no signatures key.

        Checked against the emitted bytes rather than the payload dict, because
        the bytes are what a verifier actually re-derives and compares.
        """
        req = CARD_SIGN_002
        _require_signatures(agent_card)

        canonical = canonicalize_agent_card(agent_card)
        marker = b'"' + SIGNATURES_FIELD.encode("utf-8") + b'":'

        valid = marker not in canonical
        errors = (
            []
            if valid
            else [
                f"canonical signing bytes still carry a {SIGNATURES_FIELD!r} key, "
                f"which Section 8.4.1 rule 3 requires to be excluded"
            ]
        )
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])
