"""
Test Utilities for A2A v0.3.0 Transport-Agnostic Testing

This package provides utility functions and helpers for creating transport-agnostic
tests that work across JSON-RPC, gRPC, and REST transports while maintaining
backward compatibility with existing test patterns.
"""

from .transport_helpers import (
    transport_send_message,
    transport_get_task,
    transport_cancel_task,
    transport_get_agent_card,
    is_json_rpc_success_response,
    is_json_rpc_error_response,
    extract_task_id_from_response,
    normalize_response_for_comparison,
    generate_test_message_id,
    generate_test_task_id,
)

__all__ = [
    "transport_send_message",
    "transport_get_task", 
    "transport_cancel_task",
    "transport_get_agent_card",
    "is_json_rpc_success_response",
    "is_json_rpc_error_response",
    "extract_task_id_from_response",
    "normalize_response_for_comparison",
    "generate_test_message_id",
    "generate_test_task_id",
]