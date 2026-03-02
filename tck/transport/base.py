"""Base transport client for A2A protocol operations.

This module defines the abstract base class and response dataclasses
that all transport clients (gRPC, JSON-RPC, HTTP+JSON) implement.
Method signatures match the A2A proto/JSON schema request types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class TransportResponse:
    """Response from a transport operation."""

    transport: str
    success: bool
    raw_response: Any
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int | None = None

    @property
    def is_streaming(self) -> bool:
        """Whether this response contains a stream of events."""
        return False


@dataclass
class StreamingResponse(TransportResponse):
    """Streaming response from a transport operation."""

    events: Iterator[Any] = field(default_factory=iter)

    @property
    def is_streaming(self) -> bool:
        """Whether this response contains a stream of events."""
        return True


class BaseTransportClient(ABC):
    """Abstract base class for A2A transport clients.

    Method signatures expose all parameters from the A2A proto request types.
    """

    def __init__(self, base_url: str, transport: str) -> None:
        self.base_url = base_url
        self.transport = transport

    @abstractmethod
    def send_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> TransportResponse: ...

    @abstractmethod
    def send_streaming_message(
        self,
        message: dict,
        *,
        configuration: dict | None = None,
        metadata: dict | None = None,
    ) -> StreamingResponse: ...

    @abstractmethod
    def get_task(
        self,
        id: str,
        *,
        history_length: int | None = None,
    ) -> TransportResponse: ...

    @abstractmethod
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
    ) -> TransportResponse: ...

    @abstractmethod
    def cancel_task(self, id: str) -> TransportResponse: ...

    @abstractmethod
    def subscribe_to_task(self, id: str) -> StreamingResponse: ...

    @abstractmethod
    def create_push_notification_config(
        self,
        task_id: str,
        config_id: str,
        config: dict,
    ) -> TransportResponse: ...

    @abstractmethod
    def get_push_notification_config(
        self,
        task_id: str,
        id: str,
    ) -> TransportResponse: ...

    @abstractmethod
    def list_push_notification_configs(
        self,
        task_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> TransportResponse: ...

    @abstractmethod
    def delete_push_notification_config(
        self,
        task_id: str,
        id: str,
    ) -> TransportResponse: ...

    @abstractmethod
    def get_extended_agent_card(self) -> TransportResponse: ...

    def close(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
