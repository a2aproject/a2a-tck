"""gRPC transport client for A2A protocol operations.

This module implements the gRPC transport using generated proto stubs
from the A2A specification.
"""

from __future__ import annotations

from typing import Any

import grpc

from google.protobuf.json_format import MessageToDict, ParseDict

from specification.generated import a2a_pb2, a2a_pb2_grpc
from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


def _dict_to_proto(data: dict, proto_class: type) -> Any:
    """Convert a dict to a protobuf message."""
    return ParseDict(data, proto_class())


def _proto_to_dict(message: Any) -> dict:
    """Convert a protobuf message to a dict."""
    return MessageToDict(message, preserving_proto_field_name=True)


class GrpcClient(BaseTransportClient):
    """gRPC transport client for A2A protocol."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self._channel = grpc.insecure_channel(base_url)
        self._stub = a2a_pb2_grpc.A2AServiceStub(self._channel)

    def close(self) -> None:
        self._channel.close()

    def send_message(self, request: dict) -> TransportResponse:
        try:
            proto_request = _dict_to_proto(request, a2a_pb2.SendMessageRequest)
            response = self._stub.SendMessage(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def send_streaming_message(self, request: dict) -> StreamingResponse:
        try:
            proto_request = _dict_to_proto(request, a2a_pb2.SendMessageRequest)
            stream = self._stub.SendStreamingMessage(proto_request)
            return StreamingResponse(
                transport="grpc", success=True, raw_response=stream, events=stream
            )
        except grpc.RpcError as e:
            return StreamingResponse(
                transport="grpc", success=False, raw_response=e, events=iter([]), error=str(e.details())
            )

    def get_task(self, task_id: str) -> TransportResponse:
        try:
            proto_request = _dict_to_proto({"id": task_id}, a2a_pb2.GetTaskRequest)
            response = self._stub.GetTask(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def list_tasks(self, params: dict) -> TransportResponse:
        try:
            proto_request = _dict_to_proto(params, a2a_pb2.ListTasksRequest)
            response = self._stub.ListTasks(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def cancel_task(self, task_id: str) -> TransportResponse:
        try:
            proto_request = _dict_to_proto({"id": task_id}, a2a_pb2.CancelTaskRequest)
            response = self._stub.CancelTask(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def subscribe_to_task(self, task_id: str) -> StreamingResponse:
        try:
            proto_request = _dict_to_proto({"id": task_id}, a2a_pb2.SubscribeToTaskRequest)
            stream = self._stub.SubscribeToTask(proto_request)
            return StreamingResponse(
                transport="grpc", success=True, raw_response=stream, events=stream
            )
        except grpc.RpcError as e:
            return StreamingResponse(
                transport="grpc", success=False, raw_response=e, events=iter([]), error=str(e.details())
            )

    def create_push_notification_config(self, task_id: str, config: dict) -> TransportResponse:
        try:
            data = {"task_id": task_id, **config}
            proto_request = _dict_to_proto(data, a2a_pb2.CreateTaskPushNotificationConfigRequest)
            response = self._stub.CreateTaskPushNotificationConfig(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def get_push_notification_config(self, task_id: str, config_id: str) -> TransportResponse:
        try:
            data = {"task_id": task_id, "push_notification_config_id": config_id}
            proto_request = _dict_to_proto(data, a2a_pb2.GetTaskPushNotificationConfigRequest)
            response = self._stub.GetTaskPushNotificationConfig(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def list_push_notification_configs(self, task_id: str) -> TransportResponse:
        try:
            proto_request = _dict_to_proto({"task_id": task_id}, a2a_pb2.ListTaskPushNotificationConfigRequest)
            response = self._stub.ListTaskPushNotificationConfig(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def delete_push_notification_config(self, task_id: str, config_id: str) -> TransportResponse:
        try:
            data = {"task_id": task_id, "push_notification_config_id": config_id}
            proto_request = _dict_to_proto(data, a2a_pb2.DeleteTaskPushNotificationConfigRequest)
            response = self._stub.DeleteTaskPushNotificationConfig(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )

    def get_extended_agent_card(self) -> TransportResponse:
        try:
            proto_request = a2a_pb2.GetExtendedAgentCardRequest()
            response = self._stub.GetExtendedAgentCard(proto_request)
            return TransportResponse(
                transport="grpc", success=True, raw_response=response
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport="grpc", success=False, raw_response=e, error=str(e.details())
            )
