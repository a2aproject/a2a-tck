"""Regression tests for requirement error expectations."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from specification.generated import a2a_pb2
from tck.requirements.base import CONTENT_TYPE_NOT_SUPPORTED_ERROR
from tck.requirements.core_operations import CORE_OPERATIONS_REQUIREMENTS
from tests.compatibility.core_operations.test_requirements import _validate_response


def _requirement(requirement_id: str) -> Any:
    """Return a core requirement by ID."""
    return next(requirement for requirement in CORE_OPERATIONS_REQUIREMENTS if requirement.id == requirement_id)


def _response(
    *,
    success: bool,
    error_code: int | str | None = None,
    raw_response: Any = None,
) -> SimpleNamespace:
    """Build the response surface used by the generic requirement validator."""
    return SimpleNamespace(
        success=success,
        error=None if success else "rejected",
        error_code=error_code,
        raw_response={} if raw_response is None else raw_response,
    )


@pytest.mark.parametrize(
    ("transport", "error_code"),
    [
        ("jsonrpc", -32005),
        ("http_json", 415),
        ("grpc", "INVALID_ARGUMENT"),
    ],
)
def test_core_send_003_requires_content_type_not_supported_error(
    transport: str,
    error_code: int | str,
) -> None:
    """CORE-SEND-003 must enforce the specific error named by the spec."""
    requirement = _requirement("CORE-SEND-003")

    assert requirement.expected_error is CONTENT_TYPE_NOT_SUPPORTED_ERROR
    assert (
        _validate_response(
            _response(success=False, error_code=error_code),
            transport,
            requirement,
            {},
        )
        == []
    )


def test_core_send_003_rejects_wrong_error_code() -> None:
    """CORE-SEND-003 must reject a different validation error."""
    requirement = _requirement("CORE-SEND-003")

    assert _validate_response(
        _response(success=False, error_code=-32602),
        "jsonrpc",
        requirement,
        {},
    ) == ["Expected error code -32005 (ContentTypeNotSupportedError), got -32602"]


@pytest.mark.parametrize(
    ("transport", "error_code"),
    [
        ("jsonrpc", -32602),
        ("http_json", 400),
        ("grpc", "INVALID_ARGUMENT"),
    ],
)
def test_core_multi_002a_allows_rejection_without_exact_code(
    transport: str,
    error_code: int | str,
) -> None:
    """CORE-MULTI-002a must accept rejection without inventing an exact code."""
    requirement = _requirement("CORE-MULTI-002a")

    assert requirement.allows_error is True
    assert requirement.expected_error is None
    assert (
        _validate_response(
            _response(success=False, error_code=error_code),
            transport,
            requirement,
            {},
        )
        == []
    )


@pytest.mark.parametrize(
    ("transport", "raw_response"),
    [
        ("jsonrpc", lambda context_id: {"result": {"task": {"contextId": context_id}}}),
        ("http_json", lambda context_id: {"message": {"contextId": context_id}}),
        (
            "grpc",
            lambda context_id: a2a_pb2.SendMessageResponse(
                task=a2a_pb2.Task(context_id=context_id),
            ),
        ),
    ],
)
def test_core_multi_002a_accepts_preserved_context_id(
    transport: str,
    raw_response: Any,
) -> None:
    """CORE-MULTI-002a must allow success when the client context ID is preserved."""
    requirement = _requirement("CORE-MULTI-002a")
    context_id = requirement.sample_input["message"]["contextId"]

    assert (
        _validate_response(
            _response(success=True, raw_response=raw_response(context_id)),
            transport,
            requirement,
            {},
        )
        == []
    )


def test_core_multi_002a_rejects_replaced_context_id() -> None:
    """CORE-MULTI-002a must fail when success replaces the client context ID."""
    requirement = _requirement("CORE-MULTI-002a")
    expected = requirement.sample_input["message"]["contextId"]

    assert _validate_response(
        _response(
            success=True,
            raw_response={"task": {"contextId": "server-generated-replacement"}},
        ),
        "http_json",
        requirement,
        {},
    ) == [f"Expected response field 'contextId' to equal '{expected}', got 'server-generated-replacement'"]


def test_dispatched_error_requirements_declare_error_expectations() -> None:
    """Every generic error requirement must opt into an error validation path."""
    missing_expectation = [
        requirement.id
        for requirement in CORE_OPERATIONS_REQUIREMENTS
        if "error" in requirement.tags
        and requirement.operation is not None
        and "multi-operation" not in requirement.tags
        and requirement.expected_error is None
        and not getattr(requirement, "allows_error", False)
    ]

    assert missing_expectation == []
