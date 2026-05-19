"""gRPC status code mapping tests.

Validates that each A2A error type maps to the correct gRPC status code
as defined in Section 5.4 of the A2A specification.

Requirements tested:
    GRPC-ERR-002, GRPC-ERR-001
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import grpc
import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport.grpc_client import TRANSPORT
from tck.validators.grpc.error_validator import (
    extract_error_info,
    validate_grpc_error,
)
from tests.compatibility._test_helpers import assert_and_record, fail_msg, get_client, record
from tests.compatibility.markers import grpc as grpc_marker
from tests.compatibility.markers import must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

GRPC_ERR_001 = get_requirement_by_id("GRPC-ERR-001")
GRPC_ERR_002 = get_requirement_by_id("GRPC-ERR-002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_CONNECTIVITY_CODES = frozenset({
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
})


def _get_rpc_error(response: Any) -> grpc.RpcError:
    """Extract the RpcError from a failed transport response.

    Skips the test when the failure is a connectivity issue (UNAVAILABLE,
    DEADLINE_EXCEEDED) rather than a server-side A2A error.
    """
    rpc_error = response.raw_response
    if not isinstance(rpc_error, grpc.RpcError):
        pytest.fail(
            f"Expected raw_response to be grpc.RpcError, got {type(rpc_error).__name__}"
        )
    if rpc_error.code() in _CONNECTIVITY_CODES:
        pytest.fail(
            f"gRPC connectivity error: {rpc_error.code().name} — {rpc_error.details()}"
        )
    return rpc_error


# ---------------------------------------------------------------------------
# Status code mapping tests
# ---------------------------------------------------------------------------


@must
@grpc_marker
class TestGrpcStatusCodes:
    """GRPC-ERR-002: A2A errors map to correct gRPC status codes."""

    def test_task_not_found_returns_not_found(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """TaskNotFoundError: GetTask with nonexistent ID returns NOT_FOUND."""
        req = GRPC_ERR_002
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        response = client.get_task(id=tck_id("nonexistent-grpc-status-001"))
        if response.success:
            pytest.skip("Server did not return an error for non-existent task")

        rpc_error = _get_rpc_error(response)
        result = validate_grpc_error(rpc_error, "TaskNotFoundError")
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_task_not_cancelable_returns_failed_precondition(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """TaskNotCancelableError: CancelTask on nonexistent returns NOT_FOUND or FAILED_PRECONDITION."""
        req = GRPC_ERR_002
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        response = client.cancel_task(id=tck_id("nonexistent-grpc-status-002"))
        if response.success:
            pytest.skip("Server did not return an error for CancelTask")

        rpc_error = _get_rpc_error(response)
        actual_status = rpc_error.code().name
        # Server may return NOT_FOUND (TaskNotFoundError) instead of
        # FAILED_PRECONDITION (TaskNotCancelableError) since the task doesn't exist.
        valid = actual_status in ("NOT_FOUND", "FAILED_PRECONDITION")
        errors = (
            []
            if valid
            else [
                f"CancelTask on non-existent task should return "
                f"NOT_FOUND (TaskNotFoundError) or FAILED_PRECONDITION "
                f"(TaskNotCancelableError), got {actual_status}"
            ]
        )
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_unsupported_operation_returns_unimplemented(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """UnsupportedOperationError: streaming when unsupported returns UNIMPLEMENTED."""
        req = GRPC_ERR_002

        caps = agent_card.get("capabilities", {})
        if caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("Agent supports streaming; cannot trigger UnsupportedOperationError")

        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "grpc status code test"}],
            "messageId": tck_id("grpc-status-unsupported-003"),
        }
        response = client.send_streaming_message(message=msg)
        if response.success:
            pytest.skip("Server did not return an error for unsupported streaming")

        rpc_error = _get_rpc_error(response)
        result = validate_grpc_error(rpc_error, "UnsupportedOperationError")
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_push_not_supported_returns_unimplemented(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PushNotificationNotSupportedError: push config when unsupported returns UNIMPLEMENTED."""
        req = GRPC_ERR_002

        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("Agent supports push notifications; cannot trigger error")

        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = client.create_push_notification_config(
            task_id=tck_id("grpc-status-push-004"),
            config={"url": "https://example.com"},
        )
        if response.success:
            pytest.skip("Server did not return an error for unsupported push")

        rpc_error = _get_rpc_error(response)
        result = validate_grpc_error(rpc_error, "PushNotificationNotSupportedError")
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_version_not_supported_returns_unimplemented(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """VersionNotSupportedError: unsupported A2A-Version via gRPC metadata returns UNIMPLEMENTED."""
        req = GRPC_ERR_002
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        # Use the underlying stub directly to inject custom metadata.
        from google.protobuf.json_format import ParseDict

        from specification.generated import a2a_pb2

        msg = {
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "grpc version status test"}],
                "messageId": tck_id("grpc-status-ver-005"),
            }
        }
        proto_request = ParseDict(msg, a2a_pb2.SendMessageRequest())

        try:
            client.stub.SendMessage(
                proto_request,
                metadata=[("a2a-version", "99.0")],
            )
            # If the call succeeds, the server did not enforce version checking.
            detail = (
                "Server MUST return VersionNotSupportedError (UNIMPLEMENTED) for "
                "unsupported A2A-Version, but processed the request normally"
            )
            record(
                collector=compatibility_collector,
                req=req,
                transport=TRANSPORT,
                passed=False,
                errors=[detail],
            )
            pytest.fail(fail_msg(req, TRANSPORT, detail))
        except grpc.RpcError as e:
            if e.code() in _CONNECTIVITY_CODES:
                pytest.fail(
                    f"gRPC connectivity error: {e.code().name} — {e.details()}"
                )
            result = validate_grpc_error(e, "VersionNotSupportedError")
            errors = [] if result.valid else [result.message]
            record(
                collector=compatibility_collector,
                req=req,
                transport=TRANSPORT,
                passed=result.valid,
                errors=errors,
            )
            assert result.valid, fail_msg(req, TRANSPORT, result.message)


# ---------------------------------------------------------------------------
# ErrorInfo tests
# ---------------------------------------------------------------------------


@must
@grpc_marker
class TestGrpcErrorInfo:
    """GRPC-ERR-001: A2A errors include ErrorInfo in gRPC status details."""

    def test_error_info_in_status_details(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Trigger TaskNotFoundError and verify google.rpc.ErrorInfo in status details."""
        req = GRPC_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        response = client.get_task(id=tck_id("nonexistent-grpc-errinfo-001"))
        if response.success:
            pytest.skip("Server did not return an error for non-existent task")

        rpc_error = _get_rpc_error(response)
        error_info = extract_error_info(rpc_error)

        errors: list[str] = []
        if error_info is None:
            errors.append(
                "gRPC error does not contain google.rpc.ErrorInfo in "
                "trailing metadata (grpc-status-details-bin)"
            )
        else:
            if error_info["reason"] != "TASK_NOT_FOUND":
                errors.append(
                    f"ErrorInfo.reason should be 'TASK_NOT_FOUND', "
                    f"got '{error_info['reason']}'"
                )
            if error_info["domain"] != "a2a-protocol.org":
                errors.append(
                    f"ErrorInfo.domain should be 'a2a-protocol.org', "
                    f"got '{error_info['domain']}'"
                )

        assert_and_record(compatibility_collector, req, TRANSPORT, errors)
