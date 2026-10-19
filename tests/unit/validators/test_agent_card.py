"""Custom binding identifiers must actually be URIs."""

from __future__ import annotations

import pytest

from tck.reporting.collector import CompatibilityCollector
from tck.validators.agent_card import is_protocol_binding
from tests.compatibility.agent_card import test_agent_card as card_checks


@pytest.mark.parametrize("binding", ["JSONRPC", "GRPC", "HTTP+JSON", "https://example.org/bindings/v1", "urn:example:binding:v1"])
def test_standard_and_uri_identifiers_are_valid(binding: str) -> None:
    """Allow standard names and multiple absolute URI schemes."""
    assert is_protocol_binding(binding)
    collector = CompatibilityCollector()
    card_checks.TestAgentCardProtocol().test_custom_binding_identifiers_are_uris(
        {"supportedInterfaces": [{"protocolBinding": binding}]}, collector,
    )
    result, = collector.get_results()
    assert result.passed
    assert result.level == "MUST"


@pytest.mark.parametrize("binding", [None, [], {}, "", "WEBSOCKET", "/relative/binding", "http://[bad", "bad path:x"])
def test_invalid_identifiers_are_rejected(binding: object) -> None:
    """Reject missing, relative, and malformed identifiers."""
    assert not is_protocol_binding(binding)
    collector = CompatibilityCollector()
    with pytest.raises(AssertionError):
        card_checks.TestAgentCardProtocol().test_custom_binding_identifiers_are_uris(
            {"supportedInterfaces": [{"protocolBinding": binding}]}, collector,
        )
    result, = collector.get_results()
    assert not result.passed
