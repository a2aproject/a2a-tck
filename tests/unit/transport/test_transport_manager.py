"""
Unit tests for TransportManager.

Tests the transport discovery, selection, and client management functionality
of the TransportManager class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from tck.transport.transport_manager import (
    TransportManager, 
    TransportManagerError,
    TransportSelectionStrategy
)
from tck.transport.base_client import TransportType, BaseTransportClient


class MockTransportClient(BaseTransportClient):
    """Mock transport client for testing."""
    
    def __init__(self, base_url: str, transport_type: TransportType):
        super().__init__(base_url, transport_type)
        self.closed = False
    
    def send_message(self, message, extra_headers=None):
        return {"task_id": "test-task-123"}
    
    def send_streaming_message(self, message, extra_headers=None):
        return iter([{"status": "running"}])
    
    def get_task(self, task_id, history_length=None, extra_headers=None):
        return {"task_id": task_id, "status": "completed"}
    
    def cancel_task(self, task_id, extra_headers=None):
        return {"task_id": task_id, "status": "cancelled"}
    
    def resubscribe_task(self, task_id, extra_headers=None):
        return iter([{"status": "running"}])
    
    def set_push_notification_config(self, task_id, config, extra_headers=None):
        return {"config_id": "test-config-123"}
    
    def get_push_notification_config(self, task_id, config_id, extra_headers=None):
        return {"config_id": config_id, "url": "https://example.com/webhook"}
    
    def list_push_notification_configs(self, task_id, extra_headers=None):
        return {"configs": []}
    
    def delete_push_notification_config(self, task_id, config_id, extra_headers=None):
        return {"config_id": config_id, "deleted": True}
    
    def get_authenticated_extended_card(self, extra_headers=None):
        return {"extended": True}
    
    def close(self):
        self.closed = True


@pytest.fixture
def sample_agent_card():
    """Sample Agent Card data for testing."""
    return {
        "preferredTransport": "jsonrpc",
        "endpoint": "https://example.com/jsonrpc",
        "additionalInterfaces": [
            {
                "transport": "grpc",
                "endpoint": "grpc://example.com:50051"
            },
            {
                "transport": "rest", 
                "endpoint": "https://example.com/api"
            }
        ],
        "capabilities": {
            "streaming": True,
            "pushNotifications": True
        }
    }


@pytest.fixture
def single_transport_agent_card():
    """Agent Card with only JSON-RPC transport."""
    return {
        "preferredTransport": "jsonrpc",
        "endpoint": "https://example.com/jsonrpc",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False
        }
    }


@pytest.fixture
def transport_manager():
    """TransportManager instance for testing."""
    return TransportManager("https://example.com")


@pytest.mark.core
class TestTransportManager:
    """Test cases for TransportManager."""
    
    def test_initialization(self):
        """Test TransportManager initialization."""
        manager = TransportManager("https://example.com", selection_strategy=TransportSelectionStrategy.PREFER_GRPC)
        
        assert manager.sut_base_url == "https://example.com"
        assert manager.selection_strategy == TransportSelectionStrategy.PREFER_GRPC
        assert manager._discovery_completed is False
        assert manager._supported_transports == []
        assert manager._client_cache == {}
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_discover_transports_success(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test successful transport discovery."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []  # No validation errors
        
        result = transport_manager.discover_transports()
        
        assert result is True
        assert transport_manager._discovery_completed is True
        assert len(transport_manager._supported_transports) == 3
        assert TransportType.JSON_RPC in transport_manager._supported_transports
        assert TransportType.GRPC in transport_manager._supported_transports
        assert TransportType.REST in transport_manager._supported_transports
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    def test_discover_transports_fetch_failure(self, mock_fetch, transport_manager):
        """Test transport discovery when Agent Card fetch fails."""
        mock_fetch.return_value = None
        
        with pytest.raises(TransportManagerError, match="Failed to fetch Agent Card"):
            transport_manager.discover_transports()
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_discover_transports_validation_failure(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test transport discovery when validation fails."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = ["Invalid transport configuration"]
        
        with pytest.raises(TransportManagerError, match="Agent Card transport validation failed"):
            transport_manager.discover_transports()
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_get_supported_transports(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test getting supported transports."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        transports = transport_manager.get_supported_transports()
        
        assert len(transports) == 3
        assert TransportType.JSON_RPC in transports
        assert TransportType.GRPC in transports  
        assert TransportType.REST in transports
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_get_preferred_transport(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test getting preferred transport."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        preferred = transport_manager.get_preferred_transport()
        
        assert preferred == TransportType.JSON_RPC
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_supports_transport(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test transport support checking."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        assert transport_manager.supports_transport(TransportType.JSON_RPC) is True
        assert transport_manager.supports_transport(TransportType.GRPC) is True
        assert transport_manager.supports_transport(TransportType.REST) is True
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_is_multi_transport_sut(self, mock_validate, mock_fetch, sample_agent_card, single_transport_agent_card):
        """Test multi-transport SUT detection."""
        # Test multi-transport SUT
        manager1 = TransportManager("https://example.com")
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        assert manager1.is_multi_transport_sut() is True
        
        # Test single-transport SUT
        manager2 = TransportManager("https://example.com")
        mock_fetch.return_value = single_transport_agent_card
        mock_validate.return_value = []
        
        assert manager2.is_multi_transport_sut() is False
    
    def test_transport_selection_strategies(self):
        """Test different transport selection strategies."""
        # This will be tested with mocked discover_transports
        supported_transports = [TransportType.JSON_RPC, TransportType.GRPC, TransportType.REST]
        
        # Test AGENT_PREFERRED strategy  
        manager = TransportManager("https://example.com", selection_strategy=TransportSelectionStrategy.AGENT_PREFERRED)
        manager._supported_transports = supported_transports
        manager._discovery_completed = True
        
        with patch.object(manager, 'get_preferred_transport', return_value=TransportType.GRPC):
            selected = manager._select_transport_by_strategy()
            assert selected == TransportType.GRPC
        
        # Test PREFER_JSONRPC strategy
        manager.selection_strategy = TransportSelectionStrategy.PREFER_JSONRPC
        selected = manager._select_transport_by_strategy()
        assert selected == TransportType.JSON_RPC
        
        # Test PREFER_GRPC strategy
        manager.selection_strategy = TransportSelectionStrategy.PREFER_GRPC
        selected = manager._select_transport_by_strategy()
        assert selected == TransportType.GRPC
        
        # Test PREFER_REST strategy
        manager.selection_strategy = TransportSelectionStrategy.PREFER_REST
        selected = manager._select_transport_by_strategy()
        assert selected == TransportType.REST
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_get_transport_client(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test getting transport client."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        # Mock the client creation
        mock_client = MockTransportClient("https://example.com/jsonrpc", TransportType.JSON_RPC)
        
        with patch.object(transport_manager, '_create_transport_client', return_value=mock_client):
            client = transport_manager.get_transport_client(TransportType.JSON_RPC)
            
            assert client is mock_client
            assert TransportType.JSON_RPC in transport_manager._client_cache
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_get_transport_client_unsupported(self, mock_validate, mock_fetch, transport_manager, single_transport_agent_card):
        """Test getting client for unsupported transport."""
        mock_fetch.return_value = single_transport_agent_card
        mock_validate.return_value = []
        
        with pytest.raises(TransportManagerError, match="is not supported by SUT"):
            transport_manager.get_transport_client(TransportType.GRPC)
    
    @patch('tck.transport.transport_manager.fetch_agent_card')
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_get_all_transport_clients(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test getting all transport clients."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        # Mock all client types
        mock_clients = {
            TransportType.JSON_RPC: MockTransportClient("https://example.com/jsonrpc", TransportType.JSON_RPC),
            TransportType.GRPC: MockTransportClient("grpc://example.com:50051", TransportType.GRPC),
            TransportType.REST: MockTransportClient("https://example.com/api", TransportType.REST)
        }
        
        def mock_create_client(transport_type):
            return mock_clients[transport_type]
        
        with patch.object(transport_manager, '_create_transport_client', side_effect=mock_create_client):
            clients = transport_manager.get_all_transport_clients()
            
            assert len(clients) == 3
            assert TransportType.JSON_RPC in clients
            assert TransportType.GRPC in clients
            assert TransportType.REST in clients
    
    @patch('tck.transport.transport_manager.fetch_agent_card')  
    @patch('tck.transport.transport_manager.validate_transport_consistency')
    def test_get_transport_info(self, mock_validate, mock_fetch, transport_manager, sample_agent_card):
        """Test getting transport information."""
        mock_fetch.return_value = sample_agent_card
        mock_validate.return_value = []
        
        info = transport_manager.get_transport_info()
        
        assert info["sut_base_url"] == "https://example.com"
        assert len(info["supported_transports"]) == 3
        assert info["preferred_transport"] == "jsonrpc"
        assert info["is_multi_transport"] is True
        assert info["discovery_completed"] is True
    
    def test_clear_client_cache(self, transport_manager):
        """Test clearing client cache."""
        # Add some mock clients to cache
        mock_client = MockTransportClient("https://example.com", TransportType.JSON_RPC)
        transport_manager._client_cache[TransportType.JSON_RPC] = mock_client
        
        assert len(transport_manager._client_cache) == 1
        
        transport_manager.clear_client_cache()
        
        assert len(transport_manager._client_cache) == 0
    
    def test_close(self, transport_manager):
        """Test closing transport manager."""
        # Add mock clients with close method
        mock_client = MockTransportClient("https://example.com", TransportType.JSON_RPC)
        transport_manager._client_cache[TransportType.JSON_RPC] = mock_client
        
        transport_manager.close()
        
        assert mock_client.closed is True
        assert len(transport_manager._client_cache) == 0
    
    def test_context_manager(self):
        """Test using TransportManager as context manager."""
        with TransportManager("https://example.com") as manager:
            assert manager.sut_base_url == "https://example.com"
        
        # Manager should be closed after context exit
        # (Can't easily test session.close() without more complex mocking)
    
    def test_string_representations(self, transport_manager):
        """Test string representations."""
        str_repr = str(transport_manager)
        assert "TransportManager(https://example.com" in str_repr
        
        repr_str = repr(transport_manager)
        assert "TransportManager(sut_base_url='https://example.com'" in repr_str