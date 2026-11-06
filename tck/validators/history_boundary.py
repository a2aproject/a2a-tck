"""Opt-in JSON-RPC caller/history application profile.

This module checks two *declared* controlled outcomes. It adds no protocol
requirement and cannot infer that arbitrary failed sends must leave no history.
The caller supplies complete, independent persisted readback from a history-
retaining application. See ``conformance-vectors/a2a-history-boundary-v01``.
"""

# This public profile uses NumPy documentation; repository defaults use D416.
# ruff: noqa: D416

from __future__ import annotations

import json
import logging

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, cast

from tck.requirements.base import INTERNAL_ERROR
from tck.validators.payload import extract_history


if TYPE_CHECKING:
    from tck.transport.base import TransportResponse


HistoryBoundaryOutcome = Literal["accepted-and-persisted", "rejected-and-absent-with-InternalError"]
LOGGER = logging.getLogger(__name__)


def _require(condition: bool, message: str) -> None:
    """Refuse a missing selected boundary instead of inferring success."""
    if not condition:
        raise ValueError(message)


def _same(left: Any, right: Any) -> bool:
    """Compare JSON values without equating booleans and numeric identifiers."""
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _response(response: TransportResponse) -> dict[str, Any]:
    """Require a decoded JSON-RPC response and literal boolean success state."""
    _require(response.transport == "jsonrpc", "History boundary profile requires JSON-RPC")
    _require(type(response.success) is bool, "Response success must be a boolean")
    _require(isinstance(response.raw_response, dict), "Response must contain a decoded JSON-RPC object")
    return cast("dict[str, Any]", response.raw_response)


def _task(response: TransportResponse) -> dict[str, Any]:
    """Read a complete native Task through the TCK public response interface."""
    body = _response(response)
    _require(response.success, "Persisted Task readback must succeed")
    result = body.get("result")
    _require(isinstance(result, dict), "Task response must contain a result object")
    result = cast("dict[str, Any]", result)
    task = result.get("task", result)
    _require(isinstance(task, dict), "Task result must be an object")
    task = cast("dict[str, Any]", task)
    _require(isinstance(task.get("history"), list), "Selected persisted Task requires complete history")
    _require(isinstance(response.task_id, str) and bool(response.task_id), "Task requires a nonempty id")
    _require(isinstance(response.context_id, str) and bool(response.context_id), "Task requires a nonempty contextId")
    return task


def _request(message: dict[str, Any], before: TransportResponse, readback: TransportResponse) -> None:
    """Bind the submitted user message to one already-existing native Task."""
    _require(message.get("role") == "ROLE_USER", "Selected follow-up must be a user message")
    _require(isinstance(message.get("messageId"), str) and bool(message["messageId"]), "Follow-up requires a nonempty messageId")
    _require(isinstance(message.get("parts"), list) and bool(message["parts"]), "Follow-up requires message parts")
    _require(message.get("taskId") == before.task_id == readback.task_id, "Follow-up and readback task identity differ")
    _require(
        message.get("contextId") == before.context_id == readback.context_id, "Follow-up and readback context identity differ"
    )
    _require(
        all(row.get("messageId") != message["messageId"] for row in _history(before)),
        "Follow-up messageId must be distinct from prior history",
    )
    _require(
        _pending_agent(before).get("messageId") != message["messageId"],
        "Follow-up messageId must be distinct from pending agent message",
    )


def _history(response: TransportResponse) -> list[dict[str, Any]]:
    """Use the public transport-aware extractor while rejecting malformed rows."""
    history = extract_history(response, "jsonrpc")
    _require(all(isinstance(row, dict) for row in history), "History messages must be objects")
    return history


def _accepted(send: TransportResponse, before: TransportResponse, readback: TransportResponse, message: dict[str, Any]) -> None:
    """Require one exact follow-up in committed history and the returned Task."""
    final = _task(readback)
    expected = [*_history(before), _pending_agent(before), message]
    _require(_same(_history(readback), expected), "Accepted follow-up must persist exactly once after prior history")
    _require(_same(_task(send), final), "Accepted caller Task must match persisted readback")


def _pending_agent(response: TransportResponse) -> dict[str, Any]:
    """Select the prior agent status message appended by this native fixture."""
    status = _task(response).get("status")
    _require(
        isinstance(status, dict) and status.get("state") == "TASK_STATE_INPUT_REQUIRED", "Selected prior Task must require input"
    )
    status = cast("dict[str, Any]", status)
    message = status.get("message")
    _require(
        isinstance(message, dict) and message.get("role") == "ROLE_AGENT",
        "Selected prior Task requires its pending agent message",
    )
    return cast("dict[str, Any]", message)


def _rejected(send: TransportResponse, before: TransportResponse, readback: TransportResponse, message: dict[str, Any]) -> None:
    """Require explicit native InternalError and unchanged selected persisted Task."""
    _require(send.success is False, "Rejected follow-up must expose a failed caller response")
    error = send.raw_response["error"]
    _require(isinstance(error, dict), "Rejected caller must contain an error object")
    _require(
        type(send.error_code) is int and send.error_code == INTERNAL_ERROR.expected_code("jsonrpc"),
        "Rejected follow-up must expose InternalError (-32603)",
    )
    expected_message = f"Task {message['taskId']} was modified concurrently by another writer"
    _require(send.error == expected_message, "Rejected caller must preserve the native concurrent-modification error")
    expected_detail = [
        {
            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
            "reason": "INTERNAL_ERROR",
            "domain": "a2a-protocol.org",
            "metadata": {},
        }
    ]
    _require(_same(error.get("data"), expected_detail), "Rejected caller must preserve native InternalError details")
    _require(_same(_task(readback), _task(before)), "Rejected follow-up must be absent from unchanged persisted Task")


def _caller(response: TransportResponse, request_id: str | int, outcome: HistoryBoundaryOutcome) -> None:
    """Bind the exact caller envelope without conflating boolean identifiers."""
    body = _response(response)
    _require(
        type(response.status_code) is int and response.status_code == HTTPStatus.OK, "Selected caller requires HTTP status 200"
    )
    _require(type(request_id) in (str, int) and request_id != "", "Request id must be a nonempty string or integer")
    _require(
        body.get("jsonrpc") == "2.0" and _same(body.get("id"), request_id), "Caller response does not match JSON-RPC request"
    )
    _require(
        set(body) == {"jsonrpc", "id", "result" if outcome == "accepted-and-persisted" else "error"},
        "Caller response fields differ from selected outcome",
    )


def validate_history_boundary(
    *,
    send_response: TransportResponse,
    before_response: TransportResponse,
    readback_response: TransportResponse,
    message: dict[str, Any],
    request_id: str | int,
    outcome: HistoryBoundaryOutcome,
) -> list[str]:
    """Validate one explicitly selected caller/persisted-history outcome.

    Parameters
    ----------
    send_response
        Actual decoded JSON-RPC SendMessage result, including native errors.
    before_response, readback_response
        TCK responses carrying the complete native Task before and after the
        selected send. Independent store readback may be wrapped in a public
        ``JsonRpcResponse``; this does not turn it into a network GetTask call.
    message
        Exact submitted follow-up with taskId, contextId and messageId.
    request_id
        Literal JSON-RPC request identifier, used to bind caller response.
    outcome
        Application-selected expected outcome. Both persistence and rejected
        absence are selected assumptions, not universal protocol mandates.

    Returns
    -------
    list[str]
        Empty for an intact selected boundary; otherwise the first precise
        refusal, also logged. This checks evidence consistency, not custody,
        producer acceptance, adoption, arbitrary failures or concurrency.

    See Also
    --------
    tck.validators.payload.extract_history : Public transport-aware extraction.
    """
    checks = {"accepted-and-persisted": _accepted, "rejected-and-absent-with-InternalError": _rejected}
    try:
        _require(outcome in checks, "Unknown selected history boundary outcome")
        _caller(send_response, request_id, outcome)
        _task(before_response)
        _task(readback_response)
        _request(message, before_response, readback_response)
        checks[outcome](send_response, before_response, readback_response, message)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        reason = str(error)
        LOGGER.warning("History boundary refused: %s", reason)
        return [reason]
    return []
