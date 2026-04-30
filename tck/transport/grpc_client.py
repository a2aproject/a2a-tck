"""gRPC transport client for A2A protocol operations.

This module implements the gRPC transport using generated proto stubs
from the A2A specification.
"""

from __future__ import annotations

import contextlib
import itertools

from dataclasses import dataclass
from typing import Any

import grpc

from google.protobuf.json_format import ParseDict

from specification.generated import a2a_pb2, a2a_pb2_grpc
from tck.transport._helpers import A2A_VERSION, A2A_VERSION_HEADER, _build_params
from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


def _dict_to_proto(data: dict, proto_class: type) -> Any:
    """Convert a dict to a protobuf message."""
    return ParseDict(data, proto_class())


TRANSPORT = "grpc"


class _GrpcResponseMixin:
    """Mixin that derives properties from a gRPC raw_response.

    On error, ``raw_response`` is a ``grpc.RpcError`` exception.
    On success, it is a protobuf message (``SendMessageResponse``, ``Task``, etc.).
    """

    raw_response: Any

    @property
    def error(self) -> str | None:
        if isinstance(self.raw_response, grpc.RpcError):
            return str(self.raw_response.details())
        return None

    @property
    def error_code(self) -> int | str | None:
        if isinstance(self.raw_response, grpc.RpcError):
            return self.raw_response.code().name
        return None

    @property
    def task_id(self) -> str | None:
        return _extract_grpc_task_field(self.raw_response, "id")

    @property
    def context_id(self) -> str | None:
        return _extract_grpc_task_field(self.raw_response, "context_id")


def _extract_grpc_task_field(raw: Any, field: str) -> str | None:
    """Extract a task field from a gRPC protobuf response.

    Handles both ``SendMessageResponse`` (oneof with ``task`` field) and
    ``Task`` (returned directly by GetTask / CancelTask).
    """
    try:
        payload = raw.WhichOneof("payload")
        if payload == "task":
            value = getattr(raw.task, field, None)
            if value:
                return value
    except (ValueError, AttributeError):
        pass
    value = getattr(raw, field, None)
    if value:
        return value
    return None


@dataclass
class GrpcResponse(_GrpcResponseMixin, TransportResponse):
    """gRPC transport response."""


@dataclass
class GrpcStreamingResponse(_GrpcResponseMixin, StreamingResponse):
    """gRPC streaming transport response."""


class GrpcClient(BaseTransportClient):
    """gRPC transport client for A2A protocol."""

    # gRPC status codes that indicate a broken connection worth reconnecting.
    _RETRIABLE_CODES = frozenset({
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.INTERNAL,
    })

    _METADATA = ((A2A_VERSION_HEADER.lower(), A2A_VERSION),)

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url, TRANSPORT)
        self._channel: grpc.Channel | None = None
        self._stub: a2a_pb2_grpc.A2AServiceStub | None = None
        self._connect()

    def _connect(self) -> None:
        """Create a fresh gRPC channel and stub."""
        if self._channel is not None:
            with contextlib.suppress(Exception):
                self._channel.close()
        self._channel = grpc.insecure_channel(self.base_url)
        self._stub = a2a_pb2_grpc.A2AServiceStub(self._channel)

    @property
    def stub(self) -> a2a_pb2_grpc.A2AServiceStub:
        """The gRPC service stub for direct RPC calls."""
        return self._stub

    def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel is not None:
            self._channel.close()

    # Default timeout (seconds) for streaming RPCs.  Without a deadline the
    # gRPC Python iterator can block indefinitely in certain environments
    # (e.g. pytest) even when the server has already sent data.
    _STREAMING_TIMEOUT_S = 30

    def _call_with_retry(
        self,
        rpc_name: str,
        request: Any,
        make_ok: callable,
        make_err: callable,
        *,
        timeout: float | None = None,
    ) -> TransportResponse | StreamingResponse:
        """Execute a gRPC call with one retry on connection errors.

        *make_ok* and *make_err* are called with the raw response/error to
        build the transport-specific result object.
        """
        rpc = getattr(self._stub, rpc_name)
        try:
            return make_ok(rpc(request, timeout=timeout, metadata=self._METADATA))
        except grpc.RpcError as e:
            if e.code() not in self._RETRIABLE_CODES:
                return make_err(e)
            self._connect()
            try:
                rpc = getattr(self._stub, rpc_name)
                return make_ok(rpc(request, timeout=timeout, metadata=self._METADATA))
            except grpc.RpcError as e2:
                return make_err(e2)

    def _unary_call(self, rpc_name: str, request: Any) -> TransportResponse:
        """Execute a unary gRPC call with one retry on connection errors."""
        return self._call_with_retry(
            rpc_name, request,
            make_ok=lambda r: GrpcResponse(
                transport=self.transport, success=True, raw_response=r,
            ),
            make_err=lambda e: GrpcResponse(
                transport=self.transport, success=False, raw_response=e,
            ),
        )

    def send_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> TransportResponse:
        """Send a message to the agent."""
        params = _build_params(message=message, configuration=configuration, metadata=metadata)
        proto_request = _dict_to_proto(params, a2a_pb2.SendMessageRequest)
        return self._unary_call("SendMessage", proto_request)

    def _streaming_call(self, rpc_name: str, request: Any) -> StreamingResponse:
        """Execute a streaming gRPC call with one retry on connection errors.

        Peeks at the first event to detect an empty stream early.  Any
        ``grpc.RpcError`` raised during iteration (including on the first
        ``next()`` call, where gRPC often defers the network request) bubbles
        up to the outer handler so that retriable errors trigger a reconnect
        and a second attempt.
        """
        for attempt in range(2):
            rpc = getattr(self._stub, rpc_name)
            try:
                stream = rpc(request, timeout=self._STREAMING_TIMEOUT_S, metadata=self._METADATA)
                try:
                    first = next(stream)
                except StopIteration:
                    return GrpcStreamingResponse(
                        transport=self.transport, success=True, raw_response=stream, events=iter([]),
                    )
                return GrpcStreamingResponse(
                    transport=self.transport, success=True, raw_response=stream,
                    events=itertools.chain([first], stream),
                )
            except grpc.RpcError as e:
                if e.code() not in self._RETRIABLE_CODES or attempt == 1:
                    return GrpcStreamingResponse(
                        transport=self.transport, success=False, raw_response=e, events=iter([]),
                    )
                self._connect()
        raise AssertionError("unreachable: retry loop always returns on the final attempt")

    def send_streaming_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> StreamingResponse:
        """Send a streaming message to the agent."""
        params = _build_params(message=message, configuration=configuration, metadata=metadata)
        proto_request = _dict_to_proto(params, a2a_pb2.SendMessageRequest)
        return self._streaming_call("SendStreamingMessage", proto_request)

    def get_task(
        self,
        id: str,
        *,
        history_length: int | None = None,
    ) -> TransportResponse:
        """Get a task by ID."""
        params = _build_params(id=id, history_length=history_length)
        proto_request = _dict_to_proto(params, a2a_pb2.GetTaskRequest)
        return self._unary_call("GetTask", proto_request)

    def list_tasks(
        self,
        context_id: str,
        *,
        status: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        history_length: int | None = None,
        status_timestamp_after: str | None = None,
        include_artifacts: bool | None = None,
    ) -> TransportResponse:
        """List tasks filtered by context ID."""
        params = _build_params(
            status=status,
            page_size=page_size,
            page_token=page_token,
            history_length=history_length,
            status_timestamp_after=status_timestamp_after,
            include_artifacts=include_artifacts,
        )
        params["context_id"] = context_id
        proto_request = _dict_to_proto(params, a2a_pb2.ListTasksRequest)
        return self._unary_call("ListTasks", proto_request)

    def cancel_task(self, id: str) -> TransportResponse:
        """Cancel a task by ID."""
        proto_request = _dict_to_proto({"id": id}, a2a_pb2.CancelTaskRequest)
        return self._unary_call("CancelTask", proto_request)

    def subscribe_to_task(self, id: str) -> StreamingResponse:
        """Subscribe to task updates."""
        proto_request = _dict_to_proto({"id": id}, a2a_pb2.SubscribeToTaskRequest)
        return self._streaming_call("SubscribeToTask", proto_request)

    def create_push_notification_config(
        self,
        task_id: str,
        config: dict,
    ) -> TransportResponse:
        """Create a push notification config for a task."""
        params = {"task_id": task_id, **config}
        proto_request = _dict_to_proto(params, a2a_pb2.TaskPushNotificationConfig)
        return self._unary_call("CreateTaskPushNotificationConfig", proto_request)

    def get_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Get a push notification config by task and config ID."""
        params = {"task_id": task_id, "id": id}
        proto_request = _dict_to_proto(params, a2a_pb2.GetTaskPushNotificationConfigRequest)
        return self._unary_call("GetTaskPushNotificationConfig", proto_request)

    def list_push_notification_configs(
        self,
        task_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> TransportResponse:
        """List push notification configs for a task."""
        params = _build_params(task_id=task_id, page_size=page_size, page_token=page_token)
        proto_request = _dict_to_proto(params, a2a_pb2.ListTaskPushNotificationConfigsRequest)
        return self._unary_call("ListTaskPushNotificationConfigs", proto_request)

    def delete_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Delete a push notification config by task and config ID."""
        params = {"task_id": task_id, "id": id}
        proto_request = _dict_to_proto(params, a2a_pb2.DeleteTaskPushNotificationConfigRequest)
        return self._unary_call("DeleteTaskPushNotificationConfig", proto_request)

    def get_extended_agent_card(self) -> TransportResponse:
        """Get the extended agent card."""
        proto_request = a2a_pb2.GetExtendedAgentCardRequest()
        return self._unary_call("GetExtendedAgentCard", proto_request)
