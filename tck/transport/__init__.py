"""A2A transport layer - clients, manager, and shared types."""

from tck.transport.base import (
    BaseTransportClient,
    StreamingResponse,
    TransportResponse,
)
from tck.transport.dispatch import execute_operation
from tck.transport.grpc_client import GrpcClient
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient
from tck.transport.manager import ALL_TRANSPORTS, TransportManager


__all__ = [
    "ALL_TRANSPORTS",
    "BaseTransportClient",
    "GrpcClient",
    "HttpJsonClient",
    "JsonRpcClient",
    "StreamingResponse",
    "TransportManager",
    "TransportResponse",
    "execute_operation",
]
