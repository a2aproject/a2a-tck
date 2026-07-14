"""Shared helpers for A2A transport clients."""

from __future__ import annotations

import base64
import json
import os

from typing import TYPE_CHECKING, Any, Iterator


if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx

A2A_VERSION_HEADER = "A2A-Version"
A2A_VERSION = "1.0"


def get_auth_headers(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build authentication headers from the documented environment variables.

    ``A2A_AUTH_HEADERS`` supplements the headers derived from
    ``A2A_AUTH_TYPE`` and takes precedence when the same header is present.
    """
    environment = os.environ if env is None else env
    headers: dict[str, str] = {}
    auth_type = environment.get("A2A_AUTH_TYPE", "").strip().lower()

    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {_required_auth_value(environment, 'A2A_AUTH_TOKEN')}"
    elif auth_type == "basic":
        username = _required_auth_value(environment, "A2A_AUTH_USERNAME")
        password = _required_auth_value(environment, "A2A_AUTH_PASSWORD")
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    elif auth_type in {"apikey", "custom"}:
        header_name = environment.get("A2A_AUTH_HEADER")
        if not header_name:
            header_name = "X-API-Key" if auth_type == "apikey" else None
        if not header_name:
            raise ValueError("A2A_AUTH_HEADER must be set when A2A_AUTH_TYPE is custom")
        headers[header_name] = _required_auth_value(environment, "A2A_AUTH_TOKEN")
    elif auth_type:
        raise ValueError(f"Unsupported A2A_AUTH_TYPE: {auth_type}")

    raw_headers = environment.get("A2A_AUTH_HEADERS")
    if raw_headers:
        try:
            configured_headers = json.loads(raw_headers)
        except json.JSONDecodeError as exc:
            raise ValueError("A2A_AUTH_HEADERS must contain a JSON object") from exc
        if not isinstance(configured_headers, dict) or not all(
            isinstance(name, str) and isinstance(value, str)
            for name, value in configured_headers.items()
        ):
            raise ValueError("A2A_AUTH_HEADERS must contain string header names and values")
        headers = merge_headers(headers, configured_headers)

    return merge_headers(headers)


def build_default_headers(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build headers shared by all transport clients."""
    return merge_headers({A2A_VERSION_HEADER: A2A_VERSION}, get_auth_headers(env))


def merge_headers(*header_sets: Mapping[str, str] | None) -> dict[str, str]:
    """Merge HTTP headers case-insensitively, with later values overriding."""
    merged: dict[str, str] = {}
    for headers in header_sets:
        if headers:
            merged.update({name.lower(): value for name, value in headers.items()})
    return merged


def _required_auth_value(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name)
    if not value:
        raise ValueError(f"{name} must be set when authentication is configured")
    return value


def _build_params(**kwargs: Any) -> dict:
    """Build a params dict, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _stream_sse(response: httpx.Response) -> Iterator[dict]:
    """Yield parsed SSE events from a streaming httpx response.

    Reads the response body incrementally so that events are available
    as soon as they arrive rather than waiting for the stream to close.
    """
    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if line.startswith("data:"):
            data = line[len("data:"):].strip()
            if data:
                yield json.loads(data)
