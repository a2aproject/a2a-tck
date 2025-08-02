"""
Transport Test Adapters for A2A Protocol v0.3.0

This package provides transport-agnostic test adapters that enable the same test
logic to be executed against different A2A transport protocols (JSON-RPC, gRPC, REST)
while maintaining real network communication with live SUTs.

Specification Reference: A2A Protocol v0.3.0 §3.4 - Transport Compliance Testing
"""

from .base_adapter import BaseTransportAdapter, TestContext, TestResult

__all__ = ['BaseTransportAdapter', 'TestContext', 'TestResult']