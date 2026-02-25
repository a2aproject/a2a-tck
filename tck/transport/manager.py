"""Transport manager for orchestrating A2A transport clients.

This module provides a manager that creates, selects, and manages
the lifecycle of transport clients (gRPC, JSON-RPC, HTTP+JSON).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tck.transport.grpc_client import GrpcClient
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient

_TRANSPORT_FACTORIES: dict[str, type[BaseTransportClient]] = {
    "grpc": GrpcClient,
    "jsonrpc": JsonRpcClient,
    "http_json": HttpJsonClient,
}

ALL_TRANSPORTS = list(_TRANSPORT_FACTORIES.keys())


class TransportManager:
    """Orchestrates creation, selection, and lifecycle of transport clients."""

    def __init__(
        self,
        base_url: str,
        transports: list[str] | None = None,
    ) -> None:
        self._base_url = base_url
        requested = transports if transports is not None else ALL_TRANSPORTS
        unknown = set(requested) - set(_TRANSPORT_FACTORIES)
        if unknown:
            msg = f"Unknown transport(s): {', '.join(sorted(unknown))}. Valid: {', '.join(ALL_TRANSPORTS)}"
            raise ValueError(msg)
        self._clients: dict[str, BaseTransportClient] = {
            name: _TRANSPORT_FACTORIES[name](base_url) for name in requested
        }

    def get_client(self, transport: str) -> BaseTransportClient:
        """Return the client for the given transport name.

        Raises KeyError if the transport was not configured.
        """
        try:
            return self._clients[transport]
        except KeyError:
            configured = ", ".join(sorted(self._clients))
            msg = f"Transport {transport!r} not configured. Available: {configured}"
            raise KeyError(msg) from None

    def get_all_clients(self) -> dict[str, BaseTransportClient]:
        """Return all configured transport clients."""
        return dict(self._clients)

    def close(self) -> None:
        """Close all transport clients and release resources."""
        for client in self._clients.values():
            client.close()
        self._clients.clear()
