"""
Unit tests for enhanced Agent Card utilities (v0.3.0).

Tests the v0.3.0 transport discovery and multi-transport Agent Card functionality.

Specification Reference: A2A Protocol v0.3.0 §5 - Agent Discovery
"""

import pytest
import requests
from unittest.mock import Mock

from tck import agent_card_utils
from tck.transport.base_client import TransportType

# Import the core marker
pytestmark = pytest.mark.core


class TestFetchAgentCard:
    """Test Agent Card fetching with v0.3.0 location."""
    
    def test_fetch_from_v030_location(self):
        """Test fetching Agent Card from v0.3.0 location."""
        agent_card = {
            "name": "Test Agent",
            "version": "1.0.0",
            "endpoint": "https://example.com/jsonrpc",
            "preferredTransport": "jsonrpc"
        }
        
        session = Mock()
        response_mock = Mock()
        response_mock.json.return_value = agent_card
        response_mock.raise_for_status = Mock()
        session.get.return_value = response_mock
        
        result = agent_card_utils.fetch_agent_card("https://example.com", session)
        
        assert result == agent_card
        session.get.assert_called_once_with("https://example.com/.well-known/agent-card.json", timeout=10)
    
    def test_fetch_agent_card_not_found(self):
        """Test handling when Agent Card is not found."""
        session = Mock()
        session.get.side_effect = requests.RequestException("404 Not Found")
        
        result = agent_card_utils.fetch_agent_card("https://example.com", session)
        
        assert result is None
    
    def test_fetch_agent_card_invalid_json(self):
        """Test handling of invalid JSON in Agent Card."""
        session = Mock()
        response_mock = Mock()
        response_mock.json.side_effect = ValueError("Invalid JSON")
        response_mock.raise_for_status = Mock()
        session.get.return_value = response_mock
        
        result = agent_card_utils.fetch_agent_card("https://example.com", session)
        
        assert result is None


class TestTransportDiscovery:
    """Test v0.3.0 transport discovery functions."""
    
    def test_get_supported_transports_single(self):
        """Test getting supported transports with single transport."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "endpoint": "https://example.com/jsonrpc"
        }
        
        transports = agent_card_utils.get_supported_transports(agent_card)
        
        assert transports == [TransportType.JSON_RPC]
    
    def test_get_supported_transports_multiple(self):
        """Test getting supported transports with multiple transports."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "endpoint": "https://example.com/jsonrpc",
            "additionalInterfaces": [
                {
                    "transport": "grpc",
                    "endpoint": "https://example.com:9090"
                },
                {
                    "transport": "rest",
                    "endpoint": "https://example.com/api/v1"
                }
            ]
        }
        
        transports = agent_card_utils.get_supported_transports(agent_card)
        
        assert len(transports) == 3
        assert TransportType.JSON_RPC in transports
        assert TransportType.GRPC in transports
        assert TransportType.REST in transports
    
    def test_get_supported_transports_empty(self):
        """Test getting supported transports when none declared."""
        agent_card = {"name": "Test Agent"}
        
        transports = agent_card_utils.get_supported_transports(agent_card)
        
        assert transports == []
    
    def test_get_preferred_transport(self):
        """Test getting preferred transport."""
        agent_card = {"preferredTransport": "grpc"}
        
        preferred = agent_card_utils.get_preferred_transport(agent_card)
        
        assert preferred == TransportType.GRPC
    
    def test_get_preferred_transport_none(self):
        """Test getting preferred transport when none specified."""
        agent_card = {"name": "Test Agent"}
        
        preferred = agent_card_utils.get_preferred_transport(agent_card)
        
        assert preferred is None


class TestTransportEndpoints:
    """Test transport endpoint extraction."""
    
    def test_get_transport_endpoints_main_only(self):
        """Test getting endpoints with main endpoint only."""
        agent_card = {
            "endpoint": "https://example.com/jsonrpc",
            "preferredTransport": "jsonrpc"
        }
        
        endpoints = agent_card_utils.get_transport_endpoints(agent_card)
        
        assert endpoints == {TransportType.JSON_RPC: "https://example.com/jsonrpc"}
    
    def test_get_transport_endpoints_multiple(self):
        """Test getting endpoints with multiple transports."""
        agent_card = {
            "endpoint": "https://example.com/jsonrpc",
            "additionalInterfaces": [
                {
                    "transport": "grpc",
                    "endpoint": "https://example.com:9090"
                },
                {
                    "type": "rest",
                    "url": "https://example.com/api/v1"
                }
            ]
        }
        
        endpoints = agent_card_utils.get_transport_endpoints(agent_card)
        
        expected = {
            TransportType.JSON_RPC: "https://example.com/jsonrpc",
            TransportType.GRPC: "https://example.com:9090",
            TransportType.REST: "https://example.com/api/v1"
        }
        assert endpoints == expected
    
    def test_get_transport_interface_info(self):
        """Test getting detailed interface information."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "endpoint": "https://example.com/jsonrpc",
            "additionalInterfaces": [
                {
                    "transport": "grpc",
                    "endpoint": "https://example.com:9090",
                    "metadata": {"compression": "gzip"}
                }
            ]
        }
        
        # Test preferred transport
        jsonrpc_info = agent_card_utils.get_transport_interface_info(agent_card, TransportType.JSON_RPC)
        assert jsonrpc_info == {
            "transport": "jsonrpc",
            "endpoint": "https://example.com/jsonrpc",
            "preferred": True
        }
        
        # Test additional interface
        grpc_info = agent_card_utils.get_transport_interface_info(agent_card, TransportType.GRPC)
        assert grpc_info == {
            "transport": "grpc",
            "endpoint": "https://example.com:9090",
            "metadata": {"compression": "gzip"}
        }
        
        # Test non-existent transport
        rest_info = agent_card_utils.get_transport_interface_info(agent_card, TransportType.REST)
        assert rest_info is None


class TestTransportTypeParsing:
    """Test transport type parsing and validation."""
    
    def test_parse_transport_type_jsonrpc_variants(self):
        """Test parsing various JSON-RPC transport names."""
        test_cases = ["jsonrpc", "JSON-RPC", "json-rpc", "jsonrpc2.0", "RPC"]
        
        for name in test_cases:
            result = agent_card_utils._parse_transport_type(name)
            assert result == TransportType.JSON_RPC, f"Failed for: {name}"
    
    def test_parse_transport_type_grpc_variants(self):
        """Test parsing various gRPC transport names."""
        test_cases = ["grpc", "GRPC", "gRPC", "grpc-web", "protobuf"]
        
        for name in test_cases:
            result = agent_card_utils._parse_transport_type(name)
            assert result == TransportType.GRPC, f"Failed for: {name}"
    
    def test_parse_transport_type_rest_variants(self):
        """Test parsing various REST transport names."""
        test_cases = ["rest", "REST", "http", "HTTP", "http+json", "restful"]
        
        for name in test_cases:
            result = agent_card_utils._parse_transport_type(name)
            assert result == TransportType.REST, f"Failed for: {name}"
    
    def test_parse_transport_type_unknown(self):
        """Test parsing unknown transport names."""
        unknown_names = ["websocket", "mqtt", "unknown", ""]
        
        for name in unknown_names:
            result = agent_card_utils._parse_transport_type(name)
            assert result is None, f"Should be None for: {name}"
    
    def test_has_transport_support(self):
        """Test checking transport support."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "additionalInterfaces": [
                {"transport": "grpc", "endpoint": "https://example.com:9090"}
            ]
        }
        
        assert agent_card_utils.has_transport_support(agent_card, TransportType.JSON_RPC)
        assert agent_card_utils.has_transport_support(agent_card, TransportType.GRPC)
        assert not agent_card_utils.has_transport_support(agent_card, TransportType.REST)


class TestTransportValidation:
    """Test transport configuration validation."""
    
    def test_validate_transport_consistency_valid(self):
        """Test validation of valid transport configuration."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "endpoint": "https://example.com/jsonrpc",
            "additionalInterfaces": [
                {
                    "transport": "grpc",
                    "endpoint": "https://example.com:9090"
                }
            ]
        }
        
        errors = agent_card_utils.validate_transport_consistency(agent_card)
        
        assert errors == []
    
    def test_validate_transport_consistency_no_transports(self):
        """Test validation when no transports are declared."""
        agent_card = {"name": "Test Agent"}
        
        errors = agent_card_utils.validate_transport_consistency(agent_card)
        
        assert len(errors) == 1
        assert "No supported transports declared" in errors[0]
    
    def test_validate_transport_consistency_missing_endpoint(self):
        """Test validation when transport has no endpoint."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "additionalInterfaces": [
                {
                    "transport": "grpc"
                    # Missing endpoint
                }
            ]
        }
        
        errors = agent_card_utils.validate_transport_consistency(agent_card)
        
        assert len(errors) >= 1
        assert any("no endpoint provided" in error for error in errors)
    
    def test_validate_transport_consistency_unknown_transport(self):
        """Test validation with unknown transport type."""
        agent_card = {
            "preferredTransport": "jsonrpc",
            "endpoint": "https://example.com/jsonrpc",
            "additionalInterfaces": [
                {
                    "transport": "websocket",
                    "endpoint": "wss://example.com/ws"
                }
            ]
        }
        
        errors = agent_card_utils.validate_transport_consistency(agent_card)
        
        assert len(errors) >= 1
        assert any("Unknown transport type" in error for error in errors)


if __name__ == "__main__":
    pytest.main([__file__])