"""JSON-RPC 2.0 transport client for A2A protocol operations.

This module implements the JSON-RPC 2.0 over HTTP transport,
including SSE streaming for server-push operations.
"""

from __future__ import annotations

import itertools

from dataclasses import dataclass
from typing import Any

import httpx

from tck.requirements.base import OperationType
from tck.transport._helpers import _build_params, _stream_sse
from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


TRANSPORT = "jsonrpc"


class _JsonRpcResponseMixin:
    """Mixin that derives properties from a JSON-RPC raw_response."""

    raw_response: Any

    @property
    def error(self) -> str | None:
        if isinstance(self.raw_response, dict) and "error" in self.raw_response:
            return self.raw_response["error"].get("message", str(self.raw_response["error"]))
        if isinstance(self.raw_response, Exception):
            return str(self.raw_response)
        return None

    @property
    def error_code(self) -> int | str | None:
        if isinstance(self.raw_response, dict) and "error" in self.raw_response:
            return self.raw_response["error"].get("code")
        return None

    @property
    def task_id(self) -> str | None:
        return _extract_jsonrpc_task_field(self.raw_response, "id")

    @property
    def context_id(self) -> str | None:
        return _extract_jsonrpc_task_field(self.raw_response, "contextId")


def _extract_jsonrpc_task_field(raw: Any, field: str) -> str | None:
    """Extract a task field from a JSON-RPC 2.0 response dict."""
    if not isinstance(raw, dict):
        return None
    result = raw.get("result", {})
    if not isinstance(result, dict):
        return None
    task = result.get("task", result)
    if isinstance(task, dict):
        return task.get(field)
    return None


@dataclass
class JsonRpcResponse(_JsonRpcResponseMixin, TransportResponse):
    """JSON-RPC transport response."""


@dataclass
class JsonRpcStreamingResponse(_JsonRpcResponseMixin, StreamingResponse):
    """JSON-RPC streaming transport response."""


class JsonRpcClient(BaseTransportClient):
    """JSON-RPC 2.0 over HTTP transport client for A2A protocol."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url, TRANSPORT)
        self._id_counter = itertools.count(1)
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(5.0, read=30.0),
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _next_id(self) -> int:
        """Generate the next unique request ID."""
        return next(self._id_counter)

    def _call(self, method: str, params: dict) -> TransportResponse:
        """Make a JSON-RPC 2.0 call and return a TransportResponse."""
        payload = {
            "jsonrpc": "2.0",
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
            return JsonRpcResponse(
                transport=self.transport,
                success="error" not in body,
                raw_response=body,
                headers=resp_headers,
                status_code=response.status_code,
            )
        except httpx.HTTPError as e:
            return JsonRpcResponse(
                transport=self.transport, success=False, raw_response=e,
            )

    def _call_streaming(self, method: str, params: dict) -> StreamingResponse:
        """Make a JSON-RPC 2.0 streaming call and return a StreamingResponse.

        If the server responds with ``text/event-stream``, events are yielded
        incrementally via SSE.  If the server responds with a plain JSON body
        (e.g. an immediate error before opening a stream), the body is parsed
        as a JSON-RPC response and ``success`` is set accordingly.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        try:
            request = self._client.build_request(
                "POST",
                "/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            response = self._client.send(request, stream=True)
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" not in content_type:
                # Server returned a plain JSON-RPC response (e.g. an immediate error)
                response.read()
                try:
                    body = response.json()
                except Exception:
                    body = response.text
                return JsonRpcStreamingResponse(
                    transport=self.transport,
                    success=isinstance(body, dict) and "error" not in body,
                    raw_response=body,
                    events=iter([]),
                    headers=dict(response.headers),
                    status_code=response.status_code,
                )
            return JsonRpcStreamingResponse(
                transport=self.transport,
                success=True,
                raw_response=response,
                events=_stream_sse(response),
                headers=dict(response.headers),
                status_code=response.status_code,
            )
        except httpx.ReadTimeout as e:
            return JsonRpcStreamingResponse(
                transport=self.transport, success=False, raw_response=e, events=iter([]),
                timed_out=True,
            )
        except httpx.HTTPError as e:
            return JsonRpcStreamingResponse(
                transport=self.transport, success=False, raw_response=e, events=iter([]),
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
        config: dict,
    ) -> TransportResponse:
        """Create a push notification config for a task."""
        params = {"task_id": task_id, **config}
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
