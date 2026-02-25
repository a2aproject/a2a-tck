"""Base transport client for A2A protocol operations.

This module defines the abstract base class and response dataclasses
that all transport clients (gRPC, JSON-RPC, HTTP+JSON) implement.
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

    @property
    def is_streaming(self) -> bool:
        return False


@dataclass
class StreamingResponse(TransportResponse):
    """Streaming response from a transport operation."""

    events: Iterator[Any] = field(default_factory=iter)

    @property
    def is_streaming(self) -> bool:
        return True


class BaseTransportClient(ABC):
    """Abstract base class for A2A transport clients."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    @abstractmethod
    def send_message(self, request: dict) -> TransportResponse: ...

    @abstractmethod
    def send_streaming_message(self, request: dict) -> StreamingResponse: ...

    @abstractmethod
    def get_task(self, task_id: str) -> TransportResponse: ...

    @abstractmethod
    def list_tasks(self, params: dict) -> TransportResponse: ...

    @abstractmethod
    def cancel_task(self, task_id: str) -> TransportResponse: ...

    @abstractmethod
    def subscribe_to_task(self, task_id: str) -> StreamingResponse: ...

    @abstractmethod
    def create_push_notification_config(
        self, task_id: str, config: dict
    ) -> TransportResponse: ...

    @abstractmethod
    def get_push_notification_config(
        self, task_id: str, config_id: str
    ) -> TransportResponse: ...

    @abstractmethod
    def list_push_notification_configs(
        self, task_id: str
    ) -> TransportResponse: ...

    @abstractmethod
    def delete_push_notification_config(
        self, task_id: str, config_id: str
    ) -> TransportResponse: ...

    @abstractmethod
    def get_extended_agent_card(self) -> TransportResponse: ...

    def close(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
