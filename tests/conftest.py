import os
import pytest
import tck.config
import requests
import uuid
import logging
from tck import agent_card_utils

logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    parser.addoption("--sut-url", action="store", default=None, help="URL of the SUT's A2A JSON-RPC endpoint")
    parser.addoption("--test-scope", action="store", default="core", help="Test scope: 'core' or 'all'")
    parser.addoption("--skip-agent-card", action="store_true", default=False, help="Skip fetching and validating the Agent Card")
    
    # A2A v0.3.0 transport configuration options
    parser.addoption("--transport-strategy", action="store", default="agent_preferred", 
                    help="Transport selection strategy: agent_preferred, prefer_jsonrpc, prefer_grpc, prefer_rest, all_supported")
    # --preferred-transport removed; use --transport-strategy instead
    parser.addoption("--transports", action="store", default=None,
                    help="Comma-separated list of required transports for this run: jsonrpc,grpc,rest")
    # --disabled-transports removed; if needed in future, selection will enforce it
    parser.addoption("--enable-equivalence-testing", action="store_true", default=True,
                    help="Enable transport equivalence testing for multi-transport SUTs")

def pytest_configure(config):
    sut_url = config.getoption("--sut-url")
    test_scope = config.getoption("--test-scope")
    # skip_agent_card = config.getoption("--skip-agent-card") # Not used directly in config

    if sut_url:
        tck.config.set_config(sut_url, test_scope)
    else:
        # If --sut-url is not provided, the tests requiring it will fail, which is expected.
        # The RuntimeError in get_sut_url will handle the case where it's needed but not set.
        pass
    
    # Configure A2A v0.3.0 transport settings
    transport_strategy = config.getoption("--transport-strategy")
    preferred_transport = None  # deprecated CLI option removed
    disabled_transports = None  # deprecated CLI option removed
    required_transports = config.getoption("--transports")
    enable_equivalence = config.getoption("--enable-equivalence-testing")
    
    # Set transport configuration
    tck.config.set_transport_selection_strategy(transport_strategy)
    
    # Preferred transport can still be provided via env var A2A_PREFERRED_TRANSPORT
    
    # Disabled transports can still be provided via env var A2A_DISABLED_TRANSPORTS

    # Required transports (strict mode)
    if required_transports:
        from tck.transport.base_client import TransportType
        transport_map = {
            'jsonrpc': TransportType.JSON_RPC,
            'grpc': TransportType.GRPC,
            'rest': TransportType.REST
        }
        allow_list = []
        for transport_name in required_transports.split(','):
            name = transport_name.strip().lower()
            if name in transport_map:
                allow_list.append(transport_map[name])
        if allow_list:
            tck.config.set_required_transports(allow_list)
    
    tck.config.set_enable_transport_equivalence_testing(enable_equivalence)

@pytest.fixture(scope="session")
def agent_card_data(request):
    """
    Pytest fixture to fetch the Agent Card data.
    Skips fetching if --skip-agent-card is provided.
    """
    if request.config.getoption("--skip-agent-card"):
        print("Skipping Agent Card fetch due to --skip-agent-card flag.")
        return None
        
    sut_url = request.config.getoption("--sut-url") or os.getenv("SUT_URL")
    if not sut_url:
         # This case should ideally be caught earlier, but as a fallback:
        pytest.fail("SUT URL not provided. Cannot fetch Agent Card.")

    # Use a session to potentially reuse connections
    with requests.Session() as session:
        card = agent_card_utils.fetch_agent_card(sut_url, session)
        if card is None:
            pytest.fail("Failed to fetch or parse Agent Card from the SUT. Check SUT URL and Agent Card endpoint.")
        return card

def pytest_generate_tests(metafunc):
    # This hook can be used to parametrize tests based on command line options
    # For example, if you had tests that should only run for a specific scope:
    # if "scope" in metafunc.fixturenames:
    #     metafunc.parametrize("scope", [metafunc.config.getoption("--test-scope")])
    pass

def pytest_collection_modifyitems(config, items):
    # Apply markers based on --test-scope
    if config.getoption("--test-scope") == "core":
        # Keep only items marked with 'core' or mandatory markers
        skip_all = pytest.mark.skip(reason="requires --test-scope all")
        core_markers = {"core", "mandatory", "mandatory_jsonrpc", "mandatory_protocol"}
        for item in items:
            # Check if item has any core markers
            if not any(marker in item.keywords for marker in core_markers):
                item.add_marker(skip_all)

    if config.getoption("--skip-agent-card"):
        skip_agent_card_tests = pytest.mark.skip(reason="--skip-agent-card was specified")
        for item in items:
            if "agent_card" in item.keywords or "test_agent_card" in item.name:
                 item.add_marker(skip_agent_card_tests)

    # Note: 'all' scope implicitly runs all tests not explicitly marked to be skipped

@pytest.fixture
def valid_text_message_params():
    # Minimal valid params for message/send (TextPart)
    return {
        "message": {
            "kind": "message",
            "messageId": "test-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello from TCK!"
                }
            ]
        }
    }

@pytest.fixture
def valid_file_message_params():
    # Valid params for message/send with FilePart
    # Note: mimeType is RECOMMENDED per A2A Specification §6.6.2 FileWithUri Object
    return {
        "message": {
            "kind": "message",
            "messageId": "test-file-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",  # RECOMMENDED: Media Type per A2A Spec §6.6.2
                        "url": "https://example.com/test.txt",
                        "sizeInBytes": 1024
                    }
                }
            ]
        }
    }

@pytest.fixture
def valid_data_message_params():
    # Valid params for message/send with DataPart
    return {
        "message": {
            "kind": "message",
            "messageId": "test-data-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "data",
                    "data": {
                        "key": "value",
                        "number": 123,
                        "nested": {
                            "array": [1, 2, 3]
                        }
                    }
                }
            ]
        }
    }

# =====================================================================================
# A2A v0.3.0 Transport-Aware Test Fixtures
# =====================================================================================

@pytest.fixture(scope="session")
def transport_manager(request):
    """
    Create a TransportManager instance for the test session.
    
    This fixture provides the core transport management capabilities for A2A v0.3.0
    multi-transport testing. It discovers available transports from the SUT's Agent Card
    and manages transport client selection based on configuration.
    
    Returns:
        TransportManager: Configured transport manager instance
        
    Specification Reference: A2A v0.3.0 §3.4.2 - Transport Selection and Negotiation
    """
    from tck.transport.transport_manager import TransportManager
    
    sut_url = request.config.getoption("--sut-url") or os.getenv("SUT_URL")
    if not sut_url:
        pytest.fail("SUT URL not provided. Cannot create transport manager.")
    
    # Get transport strategy from configuration
    strategy = tck.config.get_transport_selection_strategy()
    
    manager = TransportManager(sut_base_url=sut_url, selection_strategy=strategy)
    
    # Perform transport discovery during session setup
    try:
        success = manager.discover_transports()
        if not success:
            pytest.fail(f"Failed to discover transports from SUT at {sut_url}")
        # If strict required transports are configured and none are available, fail the run
        required = tck.config.get_required_transports()
        if required is not None:
            try:
                supported = manager.get_supported_transports()
            except Exception:
                supported = []
            if not supported:
                pytest.fail("Requested transport(s) not supported by SUT; failing run as required")
    except Exception as e:
        pytest.fail(f"Transport discovery failed: {e}")
    
    yield manager
    
    # Cleanup: Close all transport clients
    try:
        manager.close()
    except Exception as e:
        logger.warning(f"Error during transport manager cleanup: {e}")

@pytest.fixture(scope="function")
def sut_client(transport_manager, request):
    """
    Provide a transport client for testing based on configuration.
    
    This fixture replaces the legacy SUTClient fixture with a transport-aware
    implementation that supports A2A v0.3.0 multi-transport architecture.
    The client returned implements the BaseTransportClient interface and can
    be used with any supported transport (JSON-RPC, gRPC, REST).
    
    For backward compatibility, if only JSON-RPC is available or configured,
    this returns a client that maintains the same interface as the legacy SUTClient.
    
    Returns:
        BaseTransportClient: A transport client (JSONRPCClient, GRPCClient, or RESTClient)
        
    Specification Reference: A2A v0.3.0 §3.2 - Transport Protocols
    """
    try:
        # Get the appropriate transport client based on configuration
        # Use None to let TransportManager select based on strategy
        client = transport_manager.get_transport_client()
        if client is None:
            pytest.fail("No transport client available. Check SUT transport configuration.")
        
        return client
        
    except Exception as e:
        pytest.fail(f"Failed to create transport client: {e}")

@pytest.fixture(scope="function") 
def all_transport_clients(transport_manager, request):
    """
    Provide all available transport clients for multi-transport testing.
    
    This fixture returns a dictionary of all supported transport clients,
    enabling tests to validate functional equivalence across different
    transport protocols. Used primarily for transport equivalence testing.
    
    Returns:
        Dict[TransportType, BaseTransportClient]: Map of transport types to clients
        
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    try:
        clients = transport_manager.get_all_transport_clients()
        if not clients:
            pytest.skip("No transport clients available")
        
        return clients
        
    except Exception as e:
        pytest.fail(f"Failed to create transport clients: {e}")

@pytest.fixture(scope="function")
def multi_transport_sut(transport_manager, request):
    """
    Provide a multi-transport testing context for SUTs supporting multiple transports.
    
    This fixture is used for tests that require validation across multiple transport
    protocols. It skips automatically if the SUT only supports a single transport.
    
    Returns:
        Dict[TransportType, BaseTransportClient]: Map of available transport clients
        
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence for Multi-Transport SUTs
    """
    try:
        clients = transport_manager.get_all_transport_clients()
        
        # Skip if SUT only supports one transport
        if len(clients) < 2:
            pytest.skip(f"Multi-transport testing requires 2+ transports, found {len(clients)}")
        
        return clients
        
    except Exception as e:
        pytest.fail(f"Failed to create multi-transport context: {e}")

@pytest.fixture(scope="function")
def transport_equivalence_enabled(request):
    """
    Check if transport equivalence testing is enabled in configuration.
    
    This fixture allows tests to conditionally run equivalence tests based
    on configuration. Equivalence testing compares responses across different
    transport protocols to ensure functional consistency.
    
    Returns:
        bool: True if equivalence testing is enabled
        
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    return tck.config.get_enable_transport_equivalence_testing()

# =====================================================================================
# Backward Compatibility Fixtures 
# =====================================================================================

@pytest.fixture(scope="function")
def legacy_sut_client():
    """
    Provide the legacy SUTClient for backward compatibility.
    
    This fixture maintains compatibility with existing tests that specifically
    require the legacy SUTClient interface. New tests should use the transport-aware
    'sut_client' fixture instead.
    
    Returns:
        SUTClient: Legacy JSON-RPC client
        
    Note: This fixture is deprecated and will be removed in future versions.
    """
    from tck.sut_client import SUTClient
    return SUTClient()

# =====================================================================================
# Transport-Specific Test Support
# =====================================================================================

@pytest.fixture(scope="function")
def jsonrpc_client_only(transport_manager, request):
    """
    Provide specifically a JSON-RPC transport client.
    
    This fixture is used for tests that specifically need to validate
    JSON-RPC transport behavior, regardless of what other transports
    the SUT supports.
    
    Returns:
        JSONRPCClient: JSON-RPC transport client
        
    Specification Reference: A2A v0.3.0 §3.2.1 - JSON-RPC 2.0 Transport
    """
    from tck.transport.base_client import TransportType
    
    try:
        client = transport_manager.get_transport_client(TransportType.JSON_RPC)
        if client is None:
            pytest.skip("JSON-RPC transport not supported by SUT")
        return client
    except Exception as e:
        pytest.fail(f"Failed to create JSON-RPC client: {e}")

@pytest.fixture(scope="function")
def grpc_client_only(transport_manager, request):
    """
    Provide specifically a gRPC transport client.
    
    This fixture is used for tests that specifically need to validate
    gRPC transport behavior and Protocol Buffers communication.
    
    Returns:
        GRPCClient: gRPC transport client
        
    Specification Reference: A2A v0.3.0 §3.2.2 - gRPC Transport
    """
    from tck.transport.base_client import TransportType
    
    try:
        client = transport_manager.get_transport_client(TransportType.GRPC)
        if client is None:
            pytest.skip("gRPC transport not supported by SUT")
        return client
    except Exception as e:
        pytest.fail(f"Failed to create gRPC client: {e}")

@pytest.fixture(scope="function")
def rest_client_only(transport_manager, request):
    """
    Provide specifically a REST transport client.
    
    This fixture is used for tests that specifically need to validate
    HTTP+JSON/REST transport behavior.
    
    Returns:
        RESTClient: REST transport client
        
    Specification Reference: A2A v0.3.0 §3.2.3 - HTTP+JSON/REST Transport  
    """
    from tck.transport.base_client import TransportType
    
    try:
        client = transport_manager.get_transport_client(TransportType.REST)
        if client is None:
            pytest.skip("REST transport not supported by SUT")
        return client
    except Exception as e:
        pytest.fail(f"Failed to create REST client: {e}")
