"""Custom binding URI recommendations preserve their normative level."""

from __future__ import annotations

import pytest

from tck.reporting.collector import CompatibilityCollector
from tck.validators.agent_card import supports_input_media_type, uses_recommended_binding_identifier
from tests.compatibility.agent_card import test_agent_card as card_checks


@pytest.mark.parametrize("binding", ["https://example.org/bindings/v1", "urn:example:binding:v1"])
def test_custom_uri_identifiers_are_recommended(binding: str) -> None:
    """Multiple absolute URI schemes satisfy the recommendation."""
    assert uses_recommended_binding_identifier(binding)
    collector = CompatibilityCollector()
    card_checks.TestCustomBindingIdentifiers().test_custom_binding_identifiers_are_uris(
        {"supportedInterfaces": [{"protocolBinding": binding}]}, collector,
    )
    result, = collector.get_results()
    assert result.passed and not result.skipped
    assert result.level == "SHOULD"


@pytest.mark.parametrize("binding", ["JSONRPC", "GRPC", "HTTP+JSON"])
def test_standard_only_card_has_no_custom_binding_result(binding: str) -> None:
    """A standard-only card is inapplicable, not a vacuous custom-binding pass."""
    assert uses_recommended_binding_identifier(binding)
    collector = CompatibilityCollector()
    with pytest.raises(pytest.skip.Exception):
        card_checks.TestCustomBindingIdentifiers().test_custom_binding_identifiers_are_uris(
            {"supportedInterfaces": [{"protocolBinding": binding}]}, collector,
        )
    result, = collector.get_results()
    assert result.skipped and not result.passed
    assert result.level == "SHOULD"


@pytest.mark.parametrize("binding", [None, [], {}, "", "WEBSOCKET", "/relative/binding", "http://[bad", "bad path:x"])
def test_non_uri_identifiers_miss_the_recommendation(binding: object) -> None:
    """Names outside the recommended URI form are not promoted to MUST failures."""
    assert not uses_recommended_binding_identifier(binding)
    collector = CompatibilityCollector()
    try:
        with pytest.raises(AssertionError):
            card_checks.TestCustomBindingIdentifiers().test_custom_binding_identifiers_are_uris(
                {"supportedInterfaces": [{"protocolBinding": binding}]}, collector,
            )
    except pytest.skip.Exception as error:
        pytest.fail(f"Unexpected custom-binding probe skip: {error}")
    result, = collector.get_results()
    assert not result.passed and not result.skipped
    assert result.level == "SHOULD"


def test_custom_binding_probe_has_only_the_should_marker() -> None:
    """Selecting MUST tests cannot pull in a SHOULD through an inherited marker."""
    marks = {mark.name for mark in card_checks.TestCustomBindingIdentifiers.pytestmark}
    assert "should" in marks and "must" not in marks


@pytest.mark.parametrize("card", [
    {"skills": None}, {"skills": [12]}, {"defaultInputModes": None},
    {"defaultInputModes": "image/*"}, {"skills": [{"inputModes": {}}]},
    {"defaultInputModes": [None]}, {"skills": [{"inputModes": [""]}]},
])
def test_malformed_input_mode_declarations_fail_clearly(card: dict) -> None:
    """Invalid structure cannot be interpreted as permission to skip a negative probe."""
    with pytest.raises(ValueError):
        supports_input_media_type(card, "image/x-tck-unsupported")


def test_malformed_probe_media_type_is_a_harness_error() -> None:
    """A broken canonical probe must be repaired, not classified as unsupported."""
    with pytest.raises(ValueError, match="Probe media type"):
        supports_input_media_type({}, "invalid")
