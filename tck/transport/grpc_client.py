"""gRPC transport client for A2A protocol operations.

This module implements the gRPC transport using generated proto stubs
from the A2A specification.
"""

from __future__ import annotations

from typing import Any

import grpc

from google.protobuf.json_format import ParseDict

from specification.generated import a2a_pb2, a2a_pb2_grpc
from tck.transport._helpers import _build_params
from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


def _dict_to_proto(data: dict, proto_class: type) -> Any:
    """Convert a dict to a protobuf message."""
    return ParseDict(data, proto_class())


_TRANSPORT = "grpc"

class GrpcClient(BaseTransportClient):
    """gRPC transport client for A2A protocol."""
    def __init__(self, base_url: str) -> None:
        super().__init__(base_url, _TRANSPORT)
        self._channel = grpc.insecure_channel(base_url)
        self._stub = a2a_pb2_grpc.A2AServiceStub(self._channel)

    def close(self) -> None:
        """Close the gRPC channel."""
        self._channel.close()

    def send_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> TransportResponse:
        """Send a message to the agent."""
        try:
            params = _build_params(message=message, configuration=configuration, metadata=metadata)
            proto_request = _dict_to_proto(params, a2a_pb2.SendMessageRequest)
            response = self._stub.SendMessage(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def send_streaming_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> StreamingResponse:
        """Send a streaming message to the agent."""
        try:
            params = _build_params(message=message, configuration=configuration, metadata=metadata)
            proto_request = _dict_to_proto(params, a2a_pb2.SendMessageRequest)
            stream = self._stub.SendStreamingMessage(proto_request)
            return StreamingResponse(transport=self.transport, success=True, raw_response=stream, events=stream)
        except grpc.RpcError as e:
            return StreamingResponse(transport=self.transport, success=False, raw_response=None, events=iter([]), error=str(e.details()))

    def get_task(
        self,
        id: str,
        *,
        history_length: int | None = None,
    ) -> TransportResponse:
        """Get a task by ID."""
        try:
            params = _build_params(id=id, history_length=history_length)
            proto_request = _dict_to_proto(params, a2a_pb2.GetTaskRequest)
            response = self._stub.GetTask(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

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
        try:
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
            response = self._stub.ListTasks(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def cancel_task(self, id: str) -> TransportResponse:
        """Cancel a task by ID."""
        try:
            proto_request = _dict_to_proto({"id": id}, a2a_pb2.CancelTaskRequest)
            response = self._stub.CancelTask(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def subscribe_to_task(self, id: str) -> StreamingResponse:
        """Subscribe to task updates."""
        try:
            proto_request = _dict_to_proto({"id": id}, a2a_pb2.SubscribeToTaskRequest)
            stream = self._stub.SubscribeToTask(proto_request)
            return StreamingResponse(transport=self.transport, success=True, raw_response=stream, events=stream)
        except grpc.RpcError as e:
            return StreamingResponse(transport=self.transport, success=False, raw_response=None, events=iter([]), error=str(e.details()))

    def create_push_notification_config(
        self,
        task_id: str,
        config_id: str,
        config: dict,
    ) -> TransportResponse:
        """Create a push notification config for a task."""
        try:
            params = {"task_id": task_id, "config_id": config_id, "config": config}
            proto_request = _dict_to_proto(params, a2a_pb2.CreateTaskPushNotificationConfigRequest)
            response = self._stub.CreateTaskPushNotificationConfig(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def get_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Get a push notification config by task and config ID."""
        try:
            params = {"task_id": task_id, "id": id}
            proto_request = _dict_to_proto(params, a2a_pb2.GetTaskPushNotificationConfigRequest)
            response = self._stub.GetTaskPushNotificationConfig(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def list_push_notification_configs(
        self,
        task_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> TransportResponse:
        """List push notification configs for a task."""
        try:
            params = _build_params(task_id=task_id, page_size=page_size, page_token=page_token)
            proto_request = _dict_to_proto(params, a2a_pb2.ListTaskPushNotificationConfigRequest)
            response = self._stub.ListTaskPushNotificationConfig(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def delete_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Delete a push notification config by task and config ID."""
        try:
            params = {"task_id": task_id, "id": id}
            proto_request = _dict_to_proto(params, a2a_pb2.DeleteTaskPushNotificationConfigRequest)
            response = self._stub.DeleteTaskPushNotificationConfig(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))

    def get_extended_agent_card(self) -> TransportResponse:
        """Get the extended agent card."""
        try:
            proto_request = a2a_pb2.GetExtendedAgentCardRequest()
            response = self._stub.GetExtendedAgentCard(proto_request)
            return TransportResponse(transport=self.transport, success=True, raw_response=response)
        except grpc.RpcError as e:
            return TransportResponse(transport=self.transport, success=False, raw_response=None, error=str(e.details()))
