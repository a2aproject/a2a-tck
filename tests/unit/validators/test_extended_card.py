"""Tests for the extended-card probe classifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tck.validators.extended_card import (
    ExtendedCardProbe,
    classify_extended_card_probe,
)


@dataclass
class _FakeResponse:
    """Minimal stand-in for a TransportResponse probe result."""

    transport: str
    success: bool
    error_code: int | str | None = None
    status_code: int | None = None
    raw_response: Any = None


def _resp(
    transport: str,
    *,
    success: bool = False,
    error_code: int | str | None = None,
    status_code: int | None = None,
) -> _FakeResponse:
    return _FakeResponse(
        transport=transport,
        success=success,
        error_code=error_code,
        status_code=status_code,
    )


class TestClassifyExtendedCardProbe:
    """CARD-EXT precondition routing (A2A §3.1.11)."""

    def test_success_is_configured(self) -> None:
        """A successful response means the extended card is configured."""
        response = _resp("jsonrpc", success=True)
        assert classify_extended_card_probe(response, "jsonrpc") is ExtendedCardProbe.CONFIGURED

    def test_jsonrpc_not_configured_code(self) -> None:
        """JSON-RPC -32007 maps to the not-configured precondition."""
        response = _resp("jsonrpc", error_code=-32007)
        assert classify_extended_card_probe(response, "jsonrpc") is ExtendedCardProbe.NOT_CONFIGURED

    def test_http_json_not_configured_status(self) -> None:
        """HTTP 400 maps to the not-configured precondition on http_json."""
        response = _resp("http_json", error_code=400, status_code=400)
        assert (
            classify_extended_card_probe(response, "http_json")
            is ExtendedCardProbe.NOT_CONFIGURED
        )

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_challenge_is_auth_required(self, status: int) -> None:
        """An HTTP 401/403 auth challenge means the card exists but needs auth."""
        response = _resp("jsonrpc", error_code=-32600, status_code=status)
        assert (
            classify_extended_card_probe(response, "jsonrpc")
            is ExtendedCardProbe.AUTH_REQUIRED
        )

    @pytest.mark.parametrize("code", [-32601, -32603, -32004])
    def test_other_jsonrpc_error_is_wrong_error(self, code: int) -> None:
        """Any other A2A/JSON-RPC error is a conformance violation."""
        response = _resp("jsonrpc", error_code=code)
        assert (
            classify_extended_card_probe(response, "jsonrpc")
            is ExtendedCardProbe.WRONG_ERROR
        )

    def test_http_json_server_error_is_wrong_error(self) -> None:
        """An HTTP 500 on http_json is a conformance violation, not a skip."""
        response = _resp("http_json", error_code=500, status_code=500)
        assert (
            classify_extended_card_probe(response, "http_json")
            is ExtendedCardProbe.WRONG_ERROR
        )
