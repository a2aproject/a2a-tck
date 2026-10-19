"""Required Any structure and recommended well-known JSON-RPC error details."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import TRANSPORT
from tck.validators.error_info import uses_well_known_error_details, validate_error_details
from tests.compatibility._test_helpers import assert_and_record, get_client, record
from tests.compatibility.markers import jsonrpc, must, should


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


JSONRPC_ERR_001 = get_requirement_by_id("JSONRPC-ERR-001")
JSONRPC_ERR_003 = get_requirement_by_id("JSONRPC-ERR-003")


def _get_error_response(client: BaseTransportClient) -> dict[str, Any]:
    """Request a missing task to obtain an actual A2A-specific error."""
    response = client.get_task(id=tck_id("nonexistent-errinfo-001"))
    body = response.raw_response
    if not isinstance(body, dict) or "error" not in body:
        pytest.fail("Server did not return a JSON-RPC error for a non-existent task")
    return body


@must
@jsonrpc
class TestJsonRpcErrorDetails:
    """JSONRPC-ERR-001: error data is optional; present details are typed objects."""

    def test_present_error_data_is_any_array(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Validate present error data without requiring optional data."""
        req = JSONRPC_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        error = _get_error_response(client)["error"]
        errors = validate_error_details(error["data"]) if "data" in error else []
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)


@should
@jsonrpc
class TestJsonRpcWellKnownErrorDetails:
    """JSONRPC-ERR-003: well-known error types are recommended."""

    def test_error_data_uses_well_known_type(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Check the recommendation separately from required Any structure."""
        req = JSONRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        data = _get_error_response(client)["error"].get("data", [])
        if not data or validate_error_details(data):
            record(compatibility_collector, req, TRANSPORT, passed=False, skipped=True)
            pytest.skip("Optional error data is absent/empty or its required structure is invalid")
        errors = [] if uses_well_known_error_details(data) else ["Error details should use well-known google.rpc types"]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)
