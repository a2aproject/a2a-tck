"""Classify a GetExtendedAgentCard probe response for CARD-EXT routing.

The extended-card precondition — a server that declares ``extendedAgentCard``
support but has not configured a card — is not observable from the public
Agent Card (A2A §3.1.11).  CARD-EXT-001 and CARD-EXT-002 therefore probe the
endpoint and route on the response rather than asserting a fixed outcome.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from tck.requirements.base import EXTENDED_AGENT_CARD_NOT_CONFIGURED_ERROR


if TYPE_CHECKING:
    from tck.transport.base import TransportResponse


_AUTH_CHALLENGE_STATUS = frozenset({401, 403})
_AUTH_CHALLENGE_GRPC = frozenset({"UNAUTHENTICATED", "PERMISSION_DENIED"})


class ExtendedCardProbe(Enum):
    """Outcome of probing the GetExtendedAgentCard endpoint."""

    CONFIGURED = "configured"
    NOT_CONFIGURED = "not_configured"
    AUTH_REQUIRED = "auth_required"
    WRONG_ERROR = "wrong_error"


def classify_extended_card_probe(response: TransportResponse, transport: str) -> ExtendedCardProbe:
    """Classify a GetExtendedAgentCard probe response.

    Returns:
        ``CONFIGURED`` when the call succeeds (a card was returned);
        ``AUTH_REQUIRED`` on an auth challenge — HTTP 401/403, or the gRPC
        ``UNAUTHENTICATED``/``PERMISSION_DENIED`` statuses (gRPC responses
        carry no HTTP status code); ``NOT_CONFIGURED`` when the
        transport returns ``ExtendedAgentCardNotConfiguredError`` (the
        precondition holds); ``WRONG_ERROR`` for any other error — a
        conformance violation, since a server that declares support must
        serve the card, challenge for auth, or return the specified error.
    """
    if response.success:
        return ExtendedCardProbe.CONFIGURED
    if response.status_code in _AUTH_CHALLENGE_STATUS or response.error_code in _AUTH_CHALLENGE_GRPC:
        return ExtendedCardProbe.AUTH_REQUIRED
    expected = EXTENDED_AGENT_CARD_NOT_CONFIGURED_ERROR.expected_code(transport)
    if expected is not None and response.error_code == expected:
        return ExtendedCardProbe.NOT_CONFIGURED
    return ExtendedCardProbe.WRONG_ERROR
