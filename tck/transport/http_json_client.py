"""HTTP+JSON (REST) transport client for A2A protocol operations.

This module implements the HTTP+JSON transport binding per A2A spec Section 11,
using RESTful URLs, standard HTTP verbs, and SSE for streaming.
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from typing import Any

import httpx

from tck.requirements.base import (
    CANCEL_TASK_BINDING,
    CREATE_PUSH_CONFIG_BINDING,
    DELETE_PUSH_CONFIG_BINDING,
    GET_EXTENDED_AGENT_CARD_BINDING,
    GET_PUSH_CONFIG_BINDING,
    GET_TASK_BINDING,
    LIST_PUSH_CONFIGS_BINDING,
    LIST_TASKS_BINDING,
    PATH_MESSAGE_SEND,
    PATH_MESSAGE_STREAM,
    SEND_MESSAGE_BINDING,
    SUBSCRIBE_TO_TASK_BINDING,
)
from tck.transport._helpers import A2A_VERSION, A2A_VERSION_HEADER, _build_params, _stream_sse
from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


TRANSPORT = "http_json"
_HTTP_ERROR_MIN = 400


def _extract_error(response: httpx.Response) -> str:
    """Extract error message from an HTTP error response.

    Handles AIP-193 error format (``{"error": {"code": ..., "message": ...}}``)
    when present, otherwise falls back to the response text.
    """
    try:
        body = response.json()
        if isinstance(body, dict) and "error" in body:
            error = body["error"]
            message = error.get("message", "")
            return f"[{response.status_code}] {message}" if message else f"[{response.status_code}]"
    except (json.JSONDecodeError, ValueError):
        pass
    return f"[{response.status_code}] {response.text}"


class _HttpJsonResponseMixin:
    """Mixin that derives properties from an HTTP raw_response.

    On error, ``raw_response`` is an ``httpx.Response`` object.
    On connection failure, ``raw_response`` is an ``Exception``.
    """

    raw_response: Any
    status_code: int | None

    @property
    def error(self) -> str | None:
        if isinstance(self.raw_response, httpx.Response):
            return _extract_error(self.raw_response)
        if isinstance(self.raw_response, Exception):
            return str(self.raw_response)
        return None

    @property
    def error_code(self) -> int | str | None:
        if isinstance(self.raw_response, httpx.Response):
            return self.raw_response.status_code
        return None

    @property
    def task_id(self) -> str | None:
        return _extract_http_json_task_field(self.raw_response, "id")

    @property
    def context_id(self) -> str | None:
        return _extract_http_json_task_field(self.raw_response, "contextId")


def _extract_http_json_task_field(raw: Any, field: str) -> str | None:
    """Extract a task field from an HTTP+JSON response dict."""
    if not isinstance(raw, dict):
        return None
    task = raw.get("task", raw)
    if isinstance(task, dict):
        return task.get(field)
    return None


@dataclass
class HttpJsonResponse(_HttpJsonResponseMixin, TransportResponse):
    """HTTP+JSON transport response."""


@dataclass
class HttpJsonStreamingResponse(_HttpJsonResponseMixin, StreamingResponse):
    """HTTP+JSON streaming transport response."""


class HttpJsonClient(BaseTransportClient):
    """HTTP+JSON (REST) transport client for A2A protocol."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url, TRANSPORT)
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(5.0, read=30.0),
            headers={A2A_VERSION_HEADER: A2A_VERSION},
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> TransportResponse:
        """Make an HTTP request and return a TransportResponse."""
        try:
            response = self._client.request(
                method,
                path,
                json=json_body,
                params=params,
                headers={"Content-Type": "application/json"} if method.upper() == "POST" else None,
            )
            resp_headers = dict(response.headers)
            if response.status_code >= _HTTP_ERROR_MIN:
                return HttpJsonResponse(
                    transport=self.transport,
                    success=False,
                    raw_response=response,
                    headers=resp_headers,
                    status_code=response.status_code,
                )
            body = response.json() if response.content else {}
            return HttpJsonResponse(
                transport=self.transport,
                success=True,
                raw_response=body,
                headers=resp_headers,
                status_code=response.status_code,
            )
        except httpx.HTTPError as e:
            return HttpJsonResponse(
                transport=self.transport, success=False, raw_response=e,
            )

    def _request_streaming(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
    ) -> StreamingResponse:
        """Make an HTTP request expecting an SSE streaming response.

        Uses httpx streaming so that SSE events are yielded incrementally
        as they arrive, rather than blocking until the full body is read.
        """
        try:
            request = self._client.build_request(
                method,
                path,
                json=json_body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            response = self._client.send(request, stream=True)
            resp_headers = dict(response.headers)
            if response.status_code >= _HTTP_ERROR_MIN:
                response.close()
                return HttpJsonStreamingResponse(
                    transport=self.transport,
                    success=False,
                    raw_response=response,
                    events=iter([]),
                    headers=resp_headers,
                    status_code=response.status_code,
                )
            return HttpJsonStreamingResponse(
                transport=self.transport,
                success=True,
                raw_response=response,
                events=_stream_sse(response),
                headers=resp_headers,
                status_code=response.status_code,
            )
        except httpx.ReadTimeout as e:
            return HttpJsonStreamingResponse(
                transport=self.transport, success=False, raw_response=e, events=iter([]),
                timed_out=True,
            )
        except httpx.HTTPError as e:
            return HttpJsonStreamingResponse(
                transport=self.transport, success=False, raw_response=e, events=iter([]),
            )

    # -- Message Operations --

    def send_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> TransportResponse:
        """Send a message to the agent via ``POST /message:send``."""
        body = _build_params(message=message, configuration=configuration, metadata=metadata)
        return self._request(
            SEND_MESSAGE_BINDING.http_json_method,
            PATH_MESSAGE_SEND,
            json_body=body,
        )

    def send_streaming_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> StreamingResponse:
        """Send a streaming message to the agent via ``POST /message:stream``."""
        body = _build_params(message=message, configuration=configuration, metadata=metadata)
        return self._request_streaming(
            SEND_MESSAGE_BINDING.http_json_method,
            PATH_MESSAGE_STREAM,
            json_body=body,
        )

    # -- Task Operations --

    def get_task(
        self,
        id: str,
        *,
        history_length: int | None = None,
    ) -> TransportResponse:
        """Get a task by ID via ``GET /tasks/{id}``."""
        params = _build_params(historyLength=history_length)
        return self._request(
            GET_TASK_BINDING.http_json_method,
            GET_TASK_BINDING.http_json_path.format(id=id),
            params=params or None,
        )

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
        """List tasks filtered by context ID via ``GET /tasks``."""
        params = _build_params(
            contextId=context_id,
            status=status,
            pageSize=page_size,
            pageToken=page_token,
            historyLength=history_length,
            statusTimestampAfter=status_timestamp_after,
            includeArtifacts=str(include_artifacts).lower() if include_artifacts is not None else None,
        )
        return self._request(
            LIST_TASKS_BINDING.http_json_method,
            LIST_TASKS_BINDING.http_json_path,
            params=params,
        )

    def cancel_task(self, id: str) -> TransportResponse:
        """Cancel a task by ID via ``POST /tasks/{id}:cancel``."""
        return self._request(
            CANCEL_TASK_BINDING.http_json_method,
            CANCEL_TASK_BINDING.http_json_path.format(id=id),
        )

    def subscribe_to_task(self, id: str) -> StreamingResponse:
        """Subscribe to task updates via ``POST /tasks/{id}:subscribe``."""
        return self._request_streaming(
            SUBSCRIBE_TO_TASK_BINDING.http_json_method,
            SUBSCRIBE_TO_TASK_BINDING.http_json_path.format(id=id),
        )

    # -- Push Notification Configuration --

    def create_push_notification_config(
        self,
        task_id: str,
        config: dict,
    ) -> TransportResponse:
        """Create a push notification config via ``POST /tasks/{id}/pushNotificationConfigs``."""
        body = config
        return self._request(
            CREATE_PUSH_CONFIG_BINDING.http_json_method,
            CREATE_PUSH_CONFIG_BINDING.http_json_path.format(id=task_id),
            json_body=body,
        )

    def get_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Get a push notification config via ``GET /tasks/{id}/pushNotificationConfigs/{configId}``."""
        return self._request(
            GET_PUSH_CONFIG_BINDING.http_json_method,
            GET_PUSH_CONFIG_BINDING.http_json_path.format(id=task_id, configId=id),
        )

    def list_push_notification_configs(
        self,
        task_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> TransportResponse:
        """List push notification configs via ``GET /tasks/{id}/pushNotificationConfigs``."""
        params = _build_params(pageSize=page_size, pageToken=page_token)
        return self._request(
            LIST_PUSH_CONFIGS_BINDING.http_json_method,
            LIST_PUSH_CONFIGS_BINDING.http_json_path.format(id=task_id),
            params=params or None,
        )

    def delete_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Delete a push notification config via ``DELETE /tasks/{id}/pushNotificationConfigs/{configId}``."""
        return self._request(
            DELETE_PUSH_CONFIG_BINDING.http_json_method,
            DELETE_PUSH_CONFIG_BINDING.http_json_path.format(id=task_id, configId=id),
        )

    # -- Agent Card --

    def get_extended_agent_card(self) -> TransportResponse:
        """Get the extended agent card via ``GET /extendedAgentCard``."""
        return self._request(
            GET_EXTENDED_AGENT_CARD_BINDING.http_json_method,
            GET_EXTENDED_AGENT_CARD_BINDING.http_json_path,
        )
