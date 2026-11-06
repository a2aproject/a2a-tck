"""Agent Card signing conformance tests against a live SUT.

Validates the Section 8.4.1 canonicalization rules against the Agent Card a
server actually serves.

Requirements tested:
    CARD-SIGN-001

Signing is optional for an A2A server (Section 8.4), so this test skips when
the served card carries no ``signatures`` array.  When it does, the card's
signing payload must have an RFC 8785 canonical form at all.  A card carrying
an unpaired surrogate, a non-finite number, or a value outside the JSON data
model cannot have been canonicalized per RFC 8785, so whatever the server
signed was not the canonical form of this card.

That is the only Section 8.4.1 property decidable from the served card alone.
Whether the server excluded ``signatures`` (CARD-SIGN-002) and canonicalized
the bytes it signed is decided by verifying the JWS over the signing bytes the
TCK computes, which needs a signature-verification dependency the TCK does not
take yet.  A check that computes the signing bytes with the TCK's own functions
and then inspects them passes for every server, so none is recorded here.  The
TCK's signing-bytes computation itself is held to the a2a-jcs-v01 corpus in
``tests/unit/canonicalization/test_jcs_vectors.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.canonicalization.jcs import (
    SIGNATURES_FIELD,
    CanonicalizationError,
    canonicalize_agent_card,
)
from tck.requirements.registry import get_requirement_by_id
from tests.compatibility.markers import core, must


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CARD_SIGN_001 = get_requirement_by_id("CARD-SIGN-001")


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
            canonicalize_agent_card(agent_card)
        except CanonicalizationError as exc:
            errors.append(
                f"the served Agent Card has no RFC 8785 canonical form, so it "
                f"cannot have been canonicalized before signing: {exc}"
            )

        valid = not errors
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])
