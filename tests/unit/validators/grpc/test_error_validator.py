"""Error identity checks over real gRPC status trailers and the actual client."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING

import grpc
import pytest

from google.protobuf.any_pb2 import Any as ProtoAny
from google.rpc import error_details_pb2, status_pb2

from specification.generated import a2a_pb2, a2a_pb2_grpc
from tck.reporting.collector import CompatibilityCollector
from tck.requirements.base import ERROR_BINDINGS, VERSION_NOT_SUPPORTED_ERROR
from tck.transport.grpc_client import GrpcClient
from tck.validators.error_binding import validate_expected_error
from tck.validators.grpc.error_validator import extract_error_info, validate_grpc_error
from tests.compatibility.grpc import test_status_codes as grpc_checks


if TYPE_CHECKING:
    from collections.abc import Iterator

    from tck.requirements.base import ErrorBinding


@contextmanager
def grpc_error_client(
    code: grpc.StatusCode, details: bytes | None,
) -> Iterator[GrpcClient]:
    """Deliver a real generated GetTask error without mocking RpcError."""
    def abort(context: grpc.ServicerContext) -> None:
        if details is not None:
            context.set_trailing_metadata((("grpc-status-details-bin", details),))
        context.abort(code, "error identity control")

    class ErrorService(a2a_pb2_grpc.A2AServiceServicer):
        def GetTask(self, request: a2a_pb2.GetTaskRequest, context: grpc.ServicerContext) -> a2a_pb2.Task | None:  # noqa: N802
            if code is grpc.StatusCode.OK:
                return a2a_pb2.Task(id=request.id)
            abort(context)
            return None

        def CancelTask(self, request: a2a_pb2.CancelTaskRequest, context: grpc.ServicerContext) -> None:  # noqa: N802
            abort(context)

        def SendMessage(self, request: a2a_pb2.SendMessageRequest, context: grpc.ServicerContext) -> None:  # noqa: N802
            abort(context)

    with ThreadPoolExecutor(max_workers=1) as executor:
        server = grpc.server(executor)
        a2a_pb2_grpc.add_A2AServiceServicer_to_server(ErrorService(), server)
        port = server.add_insecure_port("127.0.0.1:0")
        server.start()
        client = GrpcClient(f"127.0.0.1:{port}")
        try:
            yield client
        finally:
            client.close()
            server.stop(0).wait()


def status_details(code: grpc.StatusCode, reason: str, domain: str = "a2a-protocol.org") -> bytes:
    """Encode the spec's google.rpc.Status/ErrorInfo structure independently."""
    detail = ProtoAny()
    detail.Pack(error_details_pb2.ErrorInfo(reason=reason, domain=domain))
    return status_pb2.Status(code=code.value[0], message="control", details=[detail]).SerializeToString()


@pytest.mark.parametrize("binding", [value for value in ERROR_BINDINGS.values() if value.reason])
def test_grpc_error_identity_round_trip(binding: ErrorBinding) -> None:
    """All released mappings require their own reason, including shared codes."""
    code = grpc.StatusCode[binding.grpc_status]
    with grpc_error_client(code, status_details(code, binding.reason)) as client:
        response = client.get_task(id="identity-control")
        assert validate_grpc_error(response.raw_response, binding.name).valid
        assert validate_expected_error(response, "grpc", binding) == []
        assert extract_error_info(response.raw_response)["reason"] == binding.reason


@pytest.mark.parametrize(
    "details",
    [None, b"\xff", status_details(grpc.StatusCode.FAILED_PRECONDITION, "UNSUPPORTED_OPERATION"),
     status_details(grpc.StatusCode.FAILED_PRECONDITION, "VERSION_NOT_SUPPORTED", "other.example"),
     status_details(grpc.StatusCode.NOT_FOUND, "VERSION_NOT_SUPPORTED")],
    ids=["missing", "malformed", "wrong-reason-same-code", "wrong-domain", "binary-code-mismatch"],
)
def test_grpc_shared_status_cannot_impersonate_an_a2a_error(details: bytes | None) -> None:
    """Both the binding probe and cross-transport producer must reject impostors."""
    with grpc_error_client(grpc.StatusCode.FAILED_PRECONDITION, details) as client:
        response = client.get_task(id="identity-control")
        assert not validate_grpc_error(response.raw_response, "VersionNotSupportedError").valid
        assert validate_expected_error(response, "grpc", VERSION_NOT_SUPPORTED_ERROR)



@pytest.mark.parametrize("reason,valid", [("VERSION_NOT_SUPPORTED", True), ("UNSUPPORTED_OPERATION", False)])
def test_grpc_compatibility_probe_uses_the_exact_error_identity(reason: str, valid: bool) -> None:
    """The real binding probe must not record a wrong shared-code error as PASS."""
    code = grpc.StatusCode.FAILED_PRECONDITION
    with grpc_error_client(code, status_details(code, reason)) as client:
        collector = CompatibilityCollector()
        try:
            with nullcontext() if valid else pytest.raises(AssertionError):
                grpc_checks.TestGrpcStatusCodes().test_version_not_supported_returns_failed_precondition({"grpc": client}, collector)
        except pytest.skip.Exception as error:
            pytest.fail(f"Unexpected gRPC compatibility-probe skip: {error}")
        result, = collector.get_results()
        assert result.passed is valid and not result.skipped


@pytest.mark.parametrize("reason,code,valid", [
    ("TASK_NOT_FOUND", grpc.StatusCode.NOT_FOUND, True),
    ("TASK_NOT_CANCELABLE", grpc.StatusCode.FAILED_PRECONDITION, False),
])
def test_cancel_missing_task_does_not_accept_an_unrelated_error(reason: str, code: grpc.StatusCode, valid: bool) -> None:
    """A non-existent task cannot be treated as an existing non-cancellable task."""
    with grpc_error_client(code, status_details(code, reason)) as client:
        collector = CompatibilityCollector()
        try:
            with nullcontext() if valid else pytest.raises(AssertionError):
                grpc_checks.TestGrpcStatusCodes().test_cancel_missing_task_returns_not_found({"grpc": client}, collector)
        except pytest.skip.Exception as error:
            pytest.fail(f"Unexpected gRPC compatibility-probe skip: {error}")
        result, = collector.get_results()
        assert result.passed is valid and not result.skipped


def test_grpc_missing_task_success_is_a_failure_not_a_skip() -> None:
    """A fabricated successful lookup cannot disappear from a mandatory error probe."""
    with grpc_error_client(grpc.StatusCode.OK, None) as client:
        collector = CompatibilityCollector()
        try:
            with pytest.raises(AssertionError):
                grpc_checks.TestGrpcStatusCodes().test_task_not_found_returns_not_found({"grpc": client}, collector)
        except pytest.skip.Exception as error:
            pytest.fail(f"Unexpected gRPC compatibility-probe skip: {error}")
        result, = collector.get_results()
        assert not result.passed and not result.skipped
