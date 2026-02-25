"""HTTP+JSON (REST) transport client for A2A protocol operations.

This module implements the HTTP+JSON transport binding per A2A spec Section 11,
using RESTful URLs, standard HTTP verbs, and SSE for streaming.
"""

from __future__ import annotations

import json

from typing import Iterator

import httpx

from tck.transport.base import BaseTransportClient, StreamingResponse, TransportResponse


_HTTP_JSON = "http_json"
_HTTP_ERROR_MIN = 400


def _build_query_params(**kwargs: object) -> dict:
    """Build a query params dict with camelCase keys, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _parse_sse(text: str) -> Iterator[dict]:
    """Parse SSE-formatted text into JSON dicts."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("data:"):
            data = line[len("data:"):].strip()
            if data:
                yield json.loads(data)


def _extract_error(response: httpx.Response) -> str:
    """Extract error message from an HTTP error response.

    Handles RFC 9457 Problem Details when Content-Type is application/problem+json,
    otherwise falls back to the response text.
    """
    content_type = response.headers.get("content-type", "")
    if "application/problem+json" in content_type:
        try:
            problem = response.json()
            detail = problem.get("detail", problem.get("title", ""))
            return f"[{response.status_code}] {detail}" if detail else f"[{response.status_code}]"
        except (json.JSONDecodeError, ValueError):
            pass
    return f"[{response.status_code}] {response.text}"


class HttpJsonClient(BaseTransportClient):
    """HTTP+JSON (REST) transport client for A2A protocol."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self._client = httpx.Client(base_url=base_url)

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
                headers={"Content-Type": "application/json"} if json_body else None,
            )
            if response.status_code >= _HTTP_ERROR_MIN:
                return TransportResponse(
                    transport=_HTTP_JSON,
                    success=False,
                    raw_response=response.json() if "json" in response.headers.get("content-type", "") else None,
                    error=_extract_error(response),
                )
            body = response.json()
            return TransportResponse(
                transport=_HTTP_JSON, success=True, raw_response=body
            )
        except httpx.HTTPError as e:
            return TransportResponse(
                transport=_HTTP_JSON, success=False, raw_response=None, error=str(e)
            )

    def _request_streaming(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
    ) -> StreamingResponse:
        """Make an HTTP request expecting an SSE streaming response."""
        try:
            response = self._client.request(
                method,
                path,
                json=json_body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            if response.status_code >= _HTTP_ERROR_MIN:
                return StreamingResponse(
                    transport=_HTTP_JSON,
                    success=False,
                    raw_response=None,
                    events=iter([]),
                    error=_extract_error(response),
                )
            return StreamingResponse(
                transport=_HTTP_JSON,
                success=True,
                raw_response=response,
                events=_parse_sse(response.text),
            )
        except httpx.HTTPError as e:
            return StreamingResponse(
                transport=_HTTP_JSON, success=False, raw_response=None, events=iter([]), error=str(e)
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
        body: dict = {"message": message}
        if configuration is not None:
            body["configuration"] = configuration
        if metadata is not None:
            body["metadata"] = metadata
        return self._request("POST", "/message:send", json_body=body)

    def send_streaming_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> StreamingResponse:
        """Send a streaming message to the agent via ``POST /message:stream``."""
        body: dict = {"message": message}
        if configuration is not None:
            body["configuration"] = configuration
        if metadata is not None:
            body["metadata"] = metadata
        return self._request_streaming("POST", "/message:stream", json_body=body)

    # -- Task Operations --

    def get_task(
        self,
        id: str,
        *,
        history_length: int | None = None,
    ) -> TransportResponse:
        """Get a task by ID via ``GET /tasks/{id}``."""
        params = _build_query_params(historyLength=history_length)
        return self._request("GET", f"/tasks/{id}", params=params or None)

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
        params = _build_query_params(
            contextId=context_id,
            status=status,
            pageSize=page_size,
            pageToken=page_token,
            historyLength=history_length,
            statusTimestampAfter=status_timestamp_after,
            includeArtifacts=str(include_artifacts).lower() if include_artifacts is not None else None,
        )
        return self._request("GET", "/tasks", params=params)

    def cancel_task(self, id: str) -> TransportResponse:
        """Cancel a task by ID via ``POST /tasks/{id}:cancel``."""
        return self._request("POST", f"/tasks/{id}:cancel")

    def subscribe_to_task(self, id: str) -> StreamingResponse:
        """Subscribe to task updates via ``POST /tasks/{id}:subscribe``."""
        return self._request_streaming("POST", f"/tasks/{id}:subscribe")

    # -- Push Notification Configuration --

    def create_push_notification_config(
        self,
        task_id: str,
        config_id: str,
        config: dict,
    ) -> TransportResponse:
        """Create a push notification config via ``POST /tasks/{id}/pushNotificationConfigs``."""
        body = {"configId": config_id, "config": config}
        return self._request("POST", f"/tasks/{task_id}/pushNotificationConfigs", json_body=body)

    def get_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Get a push notification config via ``GET /tasks/{id}/pushNotificationConfigs/{configId}``."""
        return self._request("GET", f"/tasks/{task_id}/pushNotificationConfigs/{id}")

    def list_push_notification_configs(
        self,
        task_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> TransportResponse:
        """List push notification configs via ``GET /tasks/{id}/pushNotificationConfigs``."""
        params = _build_query_params(pageSize=page_size, pageToken=page_token)
        return self._request("GET", f"/tasks/{task_id}/pushNotificationConfigs", params=params or None)

    def delete_push_notification_config(self, task_id: str, id: str) -> TransportResponse:
        """Delete a push notification config via ``DELETE /tasks/{id}/pushNotificationConfigs/{configId}``."""
        return self._request("DELETE", f"/tasks/{task_id}/pushNotificationConfigs/{id}")

    # -- Agent Card --

    def get_extended_agent_card(self) -> TransportResponse:
        """Get the extended agent card via ``GET /extendedAgentCard``."""
        return self._request("GET", "/extendedAgentCard")
