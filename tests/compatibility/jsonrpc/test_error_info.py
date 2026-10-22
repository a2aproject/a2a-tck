"""JSON-RPC ErrorInfo validation tests.

Validates that A2A-specific JSON-RPC error responses include a
google.rpc.ErrorInfo entry in the error.data array as recommended
by Section 9.5 of the A2A specification.

Requirements tested:
    JSONRPC-ERR-001, JSONRPC-ERR-003
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import TASK_NOT_FOUND_ERROR, tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import TRANSPORT
from tck.validators.error_info import find_error_info, validate_error_info
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import jsonrpc, must, should


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

JSONRPC_ERR_001 = get_requirement_by_id("JSONRPC-ERR-001")
JSONRPC_ERR_003 = get_requirement_by_id("JSONRPC-ERR-003")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_error_response(
    client: BaseTransportClient,
) -> dict[str, Any]:
    """Request a non-existent task to trigger an A2A error.

    Returns the raw JSON-RPC response dict, or skips if no error.
    """
    response = client.get_task(id=tck_id("nonexistent-errinfo-001"))
    body = response.raw_response
    if not isinstance(body, dict) or "error" not in body:
        pytest.skip("Server did not return a JSON-RPC error for non-existent task")
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@jsonrpc
class TestJsonRpcErrorData:
    """JSONRPC-ERR-001: error.data is an array of objects, each with an @type key."""

    def test_error_data_is_array(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-001: error.data, when present, is an array of objects with an @type key."""
        req = JSONRPC_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        body = _get_error_response(client)

        data = body["error"].get("data")
        errors: list[str] = []
        if data is None:
            pass  # data is optional
        elif not isinstance(data, list):
            errors.append(f"error.data must be an array, got {type(data).__name__}")
        else:
            errors.extend(
                f"error.data[{i}] must be an object with an @type key"
                for i, item in enumerate(data)
                if not isinstance(item, dict) or "@type" not in item
            )
        valid = not errors
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])


@should
@jsonrpc
class TestJsonRpcErrorInfo:
    """JSONRPC-ERR-003: A2A errors use ErrorInfo in data array."""

    def test_data_contains_error_info(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-003: data array contains a google.rpc.ErrorInfo entry."""
        req = JSONRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        body = _get_error_response(client)

        data = body["error"].get("data")
        if not isinstance(data, list):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("error.data is not an array")

        valid = find_error_info(data) is not None
        errors = (
            []
            if valid
            else [
                "data array must contain a google.rpc.ErrorInfo entry"
            ]
        )
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_error_info_valid(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-003: ErrorInfo has correct domain and valid reason."""
        req = JSONRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        body = _get_error_response(client)

        data = body["error"].get("data")
        if not isinstance(data, list):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("error.data is not an array")

        result = validate_error_info(data)
        errors = [] if result.valid else [result.message]
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, TRANSPORT, result.message)

    def test_error_info_reason_matches_condition(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-003: TaskNotFound trigger produces TASK_NOT_FOUND reason."""
        req = JSONRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        body = _get_error_response(client)

        data = body["error"].get("data")
        if not isinstance(data, list):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("error.data is not an array")

        result = validate_error_info(data, expected_reason=TASK_NOT_FOUND_ERROR.reason)
        errors = [] if result.valid else [result.message]
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, TRANSPORT, result.message)
