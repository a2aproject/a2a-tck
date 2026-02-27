"""JSON-RPC 2.0 transport client for A2A protocol operations.

This module implements the JSON-RPC 2.0 over HTTP transport,
including SSE streaming for server-push operations.
"""

from __future__ import annotations

import itertools

import httpx

from tck.requirements.base import OperationType
from tck.transport._helpers import _build_params, _parse_sse
from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


_JSONRPC = "jsonrpc"


class JsonRpcClient(BaseTransportClient):
    """JSON-RPC 2.0 over HTTP transport client for A2A protocol."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self._id_counter = itertools.count(1)
        self._client = httpx.Client(base_url=base_url)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _next_id(self) -> int:
        """Generate the next unique request ID."""
        return next(self._id_counter)

    def _call(self, method: str, params: dict) -> TransportResponse:
        """Make a JSON-RPC 2.0 call and return a TransportResponse."""
        payload = {
            _JSONRPC: "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        try:
            response = self._client.post(
                "/",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            body = response.json()
            resp_headers = dict(response.headers)
            if "error" in body:
                return TransportResponse(
                    transport=_JSONRPC,
                    success=False,
                    raw_response=body,
                    error=body["error"].get("message", str(body["error"])),
                    headers=resp_headers,
                    status_code=response.status_code,
                )
            return TransportResponse(
                transport=_JSONRPC,
                success=True,
                raw_response=body,
                headers=resp_headers,
                status_code=response.status_code,
            )
        except httpx.HTTPError as e:
            return TransportResponse(
                transport=_JSONRPC, success=False, raw_response=None, error=str(e)
            )

    def _call_streaming(self, method: str, params: dict) -> StreamingResponse:
        """Make a JSON-RPC 2.0 streaming call and return a StreamingResponse."""
        payload = {
            _JSONRPC: "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        try:
            response = self._client.post(
                "/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            return StreamingResponse(
                transport=_JSONRPC,
                success=True,
                raw_response=response,
                events=_parse_sse(response.text),
                headers=dict(response.headers),
                status_code=response.status_code,
            )
        except httpx.HTTPError as e:
            return StreamingResponse(
                transport=_JSONRPC, success=False, raw_response=None, events=iter([]), error=str(e)
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
        return self._call(OperationType.SEND_MESSAGE.value, params)

    def send_streaming_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> StreamingResponse:
        """Send a streaming message to the agent."""
        params = _build_params(message=message, configuration=configuration, metadata=metadata)
        return self._call_streaming(OperationType.SEND_STREAMING_MESSAGE.value, params)

    def get_task(
        self,
        id: str,
        *,
        history_length: int | None = None,
    ) -> TransportResponse:
        """Get a task by ID."""
        params = _build_params(id=id, history_length=history_length)
        return self._call(OperationType.GET_TASK.value, params)

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
        return self._call(OperationType.LIST_TASKS.value, params)

    def cancel_task(self, id: str) -> TransportResponse:
        """Cancel a task by ID."""
        return self._call(OperationType.CANCEL_TASK.value, {"id": id})

    def subscribe_to_task(self, id: str) -> StreamingResponse:
        """Subscribe to task updates."""
        return self._call_streaming(OperationType.SUBSCRIBE_TO_TASK.value, {"id": id})

    def create_push_notification_config(
        self,
        task_id: str,
        config_id: str,
        config: dict,
    ) -> TransportResponse:
        """Create a push notification config for a task."""
        params = {"task_id": task_id, "config_id": config_id, "config": config}
        return self._call(OperationType.CREATE_PUSH_CONFIG.value, params)

    def get_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Get a push notification config by task and config ID."""
        return self._call(OperationType.GET_PUSH_CONFIG.value, {"task_id": task_id, "id": id})

    def list_push_notification_configs(
        self,
        task_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> TransportResponse:
        """List push notification configs for a task."""
        params = _build_params(task_id=task_id, page_size=page_size, page_token=page_token)
        return self._call(OperationType.LIST_PUSH_CONFIGS.value, params)

    def delete_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Delete a push notification config by task and config ID."""
        return self._call(OperationType.DELETE_PUSH_CONFIG.value, {"task_id": task_id, "id": id})

    def get_extended_agent_card(self) -> TransportResponse:
        """Get the extended agent card."""
        return self._call(OperationType.GET_EXTENDED_AGENT_CARD.value, {})
