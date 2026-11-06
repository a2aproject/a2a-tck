"""Agent card signing conformance tests (A2A spec Section 8.4).

Fulfils backlog TASK-29 by automating the CARD-SIGN-* requirements that were
previously declared but untested.

Requirements tested:
    CARD-SIGN-001 (JCS canonicalization), CARD-SIGN-002 (signatures excluded),
    CARD-SIGN-003 (protected header parameters).

Signing is OPTIONAL (spec Section 8.4: cards **MAY** be signed), so each test
skips when the card carries no ``signatures`` array.  Verification requires the
``signing`` optional dependency group; the module skips when it is absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest


pytest.importorskip("jwcrypto")
pytest.importorskip("rfc8785")

from tck.requirements.registry import get_requirement_by_id
from tck.validators.card_signature import (
    check_signature_headers,
    verify_card_signatures,
)
from tests.compatibility.markers import core, must


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec


CARD_SIGN_001 = get_requirement_by_id("CARD-SIGN-001")
CARD_SIGN_002 = get_requirement_by_id("CARD-SIGN-002")
CARD_SIGN_003 = get_requirement_by_id("CARD-SIGN-003")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fail_msg(req: RequirementSpec, detail: str) -> str:
    return f"{req.id} [{req.title}]: {detail} (see {req.spec_url})"


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


def _skip_if_unsigned(card: dict[str, Any]) -> None:
    if not card.get("signatures"):
        pytest.skip("Agent card carries no signatures; signing is OPTIONAL (spec 8.4)")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@core
class TestAgentCardSignatureHeaders:
    """CARD-SIGN-003: JWS protected header includes alg and kid."""

    def test_protected_headers_well_formed(
        self,
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """Every signature's protected header declares alg and kid."""
        req = CARD_SIGN_003
        _skip_if_unsigned(agent_card)
        errors = check_signature_headers(agent_card)
        _record(collector=compatibility_collector, req=req, passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))


@must
@core
class TestAgentCardSignatureVerification:
    """CARD-SIGN-001 / CARD-SIGN-002: signature verifies over the JCS payload."""

    def test_signature_verifies(
        self,
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """At least one signature verifies over the canonical JCS payload."""
        _skip_if_unsigned(agent_card)
        # Verification stays offline: no jku fetcher is wired in, so a card whose
        # key is not in a trusted store is inconclusive rather than triggering a
        # network fetch of attacker-controlled `jku` content (SSRF surface).
        outcome = verify_card_signatures(agent_card)
        if outcome.inconclusive:
            pytest.skip(
                "No verification key resolvable offline (signature key not in a trusted store); cannot assert signature validity"
            )
        # A passing verification demonstrates both JCS canonicalization
        # (CARD-SIGN-001) and signatures-field exclusion (CARD-SIGN-002).
        for req in (CARD_SIGN_001, CARD_SIGN_002):
            _record(
                collector=compatibility_collector,
                req=req,
                passed=outcome.verified,
                errors=outcome.errors,
            )
        assert outcome.verified, _fail_msg(CARD_SIGN_001, "; ".join(outcome.errors))
