"""Agent Card caching header validation tests.

Validates that Agent Card HTTP endpoints include appropriate caching
headers as recommended by Section 8.6 of the A2A specification.

Requirements tested:
    CARD-CACHE-001, CARD-CACHE-002, CARD-CACHE-003
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from tck.requirements.registry import get_requirement_by_id
from tests.compatibility.markers import core, may, should


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CARD_CACHE_001 = get_requirement_by_id("CARD-CACHE-001")
CARD_CACHE_002 = get_requirement_by_id("CARD-CACHE-002")
CARD_CACHE_003 = get_requirement_by_id("CARD-CACHE-003")


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


def _fetch_agent_card(sut_host: str) -> httpx.Response:
    """Fetch the agent card and return the raw HTTP response."""
    base = sut_host.rstrip("/")
    url = f"{base}/.well-known/agent-card.json"
    response = httpx.get(url)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# Cache-Control tests (CARD-CACHE-001)
# ---------------------------------------------------------------------------


@should
@core
class TestAgentCardCacheControl:
    """CARD-CACHE-001: Agent Card endpoint includes Cache-Control header."""

    def test_cache_control_present(
        self,
        sut_host: str,
        compatibility_collector: Any,
    ) -> None:
        """CARD-CACHE-001: Response includes a Cache-Control header."""
        req = CARD_CACHE_001
        response = _fetch_agent_card(sut_host)

        cache_control = response.headers.get("cache-control")
        valid = cache_control is not None
        errors = (
            []
            if valid
            else [
                "Agent Card response should include a Cache-Control header"
            ]
        )
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])

    def test_cache_control_has_max_age(
        self,
        sut_host: str,
        compatibility_collector: Any,
    ) -> None:
        """CARD-CACHE-001: Cache-Control header includes max-age directive."""
        req = CARD_CACHE_001
        response = _fetch_agent_card(sut_host)

        cache_control = response.headers.get("cache-control", "")
        valid = "max-age" in cache_control.lower()
        errors = (
            []
            if valid
            else [
                f"Cache-Control should include max-age directive, "
                f"got: {cache_control!r}"
            ]
        )
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])


# ---------------------------------------------------------------------------
# ETag tests (CARD-CACHE-002)
# ---------------------------------------------------------------------------


@should
@core
class TestAgentCardETag:
    """CARD-CACHE-002: Agent Card endpoint includes ETag header."""

    def test_etag_present(
        self,
        sut_host: str,
        compatibility_collector: Any,
    ) -> None:
        """CARD-CACHE-002: Response includes an ETag header."""
        req = CARD_CACHE_002
        response = _fetch_agent_card(sut_host)

        etag = response.headers.get("etag")
        valid = etag is not None
        errors = (
            []
            if valid
            else [
                "Agent Card response should include an ETag header"
            ]
        )
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])


# ---------------------------------------------------------------------------
# Last-Modified tests (CARD-CACHE-003)
# ---------------------------------------------------------------------------


@may
@core
class TestAgentCardLastModified:
    """CARD-CACHE-003: Agent Card endpoint may include Last-Modified header."""

    def test_last_modified_present(
        self,
        sut_host: str,
        compatibility_collector: Any,
    ) -> None:
        """CARD-CACHE-003: Response includes a Last-Modified header."""
        req = CARD_CACHE_003
        response = _fetch_agent_card(sut_host)

        last_modified = response.headers.get("last-modified")
        valid = last_modified is not None
        errors = (
            []
            if valid
            else [
                "Agent Card response may include a Last-Modified header"
            ]
        )
        _record(collector=compatibility_collector, req=req,
                passed=valid, errors=errors)
        assert valid, _fail_msg(req, errors[0])
