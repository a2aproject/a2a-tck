"""Tests for text parts refused by an agent whose Agent Card declares no text input."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from tck.reporting.collector import CompatibilityCollector
from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import JsonRpcResponse
from tck.validators.json_schema import JSONSchemaValidator
from tck.validators.jsonrpc.response_validator import JsonRpcResponseValidator
from tests.compatibility.core_operations import test_requirements as runner
from tests.compatibility.core_operations import test_transport_behavior as transport_checks


if TYPE_CHECKING:
    from collections.abc import Callable


_CONTENT_TYPE_NOT_SUPPORTED = -32005
_TASK_NOT_FOUND = -32001

_JSON_ONLY_CARD = {"defaultInputModes": ["application/json"], "skills": [{"id": "s", "inputModes": ["application/json"]}]}
_TEXT_DEFAULT_CARD = {"defaultInputModes": ["text/plain"], "skills": []}
_TEXT_SKILL_CARD = {"defaultInputModes": ["application/json"], "skills": [{"id": "s", "inputModes": ["text/*"]}]}
_MALFORMED_CARD = {"defaultInputModes": "application/json", "skills": []}


def _error_response(code: int) -> JsonRpcResponse:
    return JsonRpcResponse(
        transport="jsonrpc",
        success=False,
        raw_response={"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": "refused"}},
    )


class _RefusingClient:
    """Answers every message with one JSON-RPC error."""

    transport = "jsonrpc"

    def __init__(self, code: int) -> None:
        self.code = code

    def send_message(self, *_args: Any, **_kwargs: Any) -> JsonRpcResponse:
        return _error_response(self.code)


def _validators() -> dict[str, Any]:
    schema = JSONSchemaValidator(Path(__file__).parents[2] / "specification" / "a2a.json")
    return {"jsonrpc": JsonRpcResponseValidator(schema)}


def _outcome(check: Callable[[], None]) -> str:
    """Name the outcome of a compatibility check instead of letting it apply to this unit test."""
    try:
        check()
    except pytest.skip.Exception as error:
        return "skip" if "declares no text/plain input mode" in str(error) else f"skip: {error}"
    except pytest.xfail.Exception:
        return "xfail"
    except AssertionError:
        return "fail"
    return "pass"


def _run(test: Any, requirement_id: str, card: dict[str, Any], code: int, collector: CompatibilityCollector) -> str:
    return _outcome(lambda: test(
        transport="jsonrpc",
        requirement=get_requirement_by_id(requirement_id),
        transport_clients={"jsonrpc": _RefusingClient(code)},
        validators=_validators(),
        compatibility_collector=collector,
        agent_card=card,
    ))


@pytest.mark.parametrize("test", [runner.test_must_requirement, runner.test_should_requirement, runner.test_may_requirement])
def test_requirement_skips_when_card_declares_no_text_input(test: Any) -> None:
    """A refused text part skips and records the requirement when the card declares no text input."""
    collector = CompatibilityCollector()
    assert _run(test, "CORE-SEND-001", _JSON_ONLY_CARD, _CONTENT_TYPE_NOT_SUPPORTED, collector) == "skip"
    result, = collector.get_results()
    assert (result.requirement_id, result.passed, result.skipped) == ("CORE-SEND-001", False, True)


@pytest.mark.parametrize(
    ("card", "code"),
    [
        (_TEXT_DEFAULT_CARD, _CONTENT_TYPE_NOT_SUPPORTED),
        (_TEXT_SKILL_CARD, _CONTENT_TYPE_NOT_SUPPORTED),
        (_MALFORMED_CARD, _CONTENT_TYPE_NOT_SUPPORTED),
        (_JSON_ONLY_CARD, _TASK_NOT_FOUND),
    ],
    ids=["text-default", "text-in-skill", "malformed-card", "other-error"],
)
def test_requirement_still_fails_on_other_refusals(card: dict[str, Any], code: int) -> None:
    """A card that declares text input, a malformed card or another error keeps the failure."""
    collector = CompatibilityCollector()
    assert _run(runner.test_must_requirement, "CORE-SEND-001", card, code, collector) == "fail"
    result, = collector.get_results()
    assert (result.passed, result.skipped) == (False, False)


def test_requirement_without_text_part_is_not_skipped() -> None:
    """A requirement that sends no text part still checks the ContentTypeNotSupportedError it expects."""
    collector = CompatibilityCollector()
    assert _run(runner.test_must_requirement, "CORE-SEND-003", _JSON_ONLY_CARD, _CONTENT_TYPE_NOT_SUPPORTED, collector) == "pass"
    result, = collector.get_results()
    assert (result.requirement_id, result.passed, result.skipped) == ("CORE-SEND-003", True, False)


@pytest.mark.parametrize(("card", "outcome"), [(_JSON_ONLY_CARD, "skip"), (_TEXT_DEFAULT_CARD, "fail")], ids=["json-only", "text-default"])
def test_jsonrpc_envelope_check_skips_only_undeclared_text(card: dict[str, Any], outcome: str) -> None:
    """JSONRPC-FMT-001 skips the same refusal and still fails when the card declares text input."""
    collector = CompatibilityCollector()
    check = transport_checks.TestJsonRpcFormat().test_response_validates_jsonrpc_envelope
    assert _outcome(lambda: check(_error_response(_CONTENT_TYPE_NOT_SUPPORTED), _validators(), collector, card)) == outcome
    result, = collector.get_results()
    assert (result.requirement_id, result.passed, result.skipped) == ("JSONRPC-FMT-001", False, outcome == "skip")
