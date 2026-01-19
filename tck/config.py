"""
Configuration module for A2A TCK v0.3.0

Handles global configuration including transport-specific settings,
test scope configuration, and environment variable management for
multi-transport testing scenarios.

Specification Reference: A2A Protocol v0.3.0 §3.4 - Transport Configuration
"""

import os
import base64
import json
import logging

from typing import Optional, Dict, List
from tck.transport.base_client import TransportType

# These will be set by pytest via conftest.py
_sut_url: Optional[str] = None
_test_scope: str = "core"

# Transport configuration - A2A v0.3.0 multi-transport support
_transport_selection_strategy: str = "agent_preferred"
_preferred_transport: Optional[TransportType] = None
_disabled_transports: List[TransportType] = []
_required_transports: Optional[List[TransportType]] = None
_transport_specific_config: Dict[str, Dict[str, str]] = {}
_enable_transport_equivalence_testing: bool = True


def set_config(sut_url: str, test_scope: str = "core"):
    """
    Set basic TCK configuration.

    Args:
        sut_url: Base URL of the SUT
        test_scope: Test scope ('core' or 'all')
    """
    global _sut_url, _test_scope
    _sut_url = sut_url
    _test_scope = test_scope


def get_sut_url() -> str:
    """
    Get the configured SUT URL.

    Returns:
        The SUT base URL

    Raises:
        RuntimeError: If SUT URL is not configured
    """
    global _sut_url
    if _sut_url is None:
        _sut_url = os.getenv("SUT_URL")
    if _sut_url is None:
        raise RuntimeError("SUT URL is not configured. Did you forget to pass --sut-url?")
    return _sut_url


def get_test_scope() -> str:
    """
    Get the configured test scope.

    Returns:
        Test scope string ('core' or 'all')
    """
    return _test_scope


# Authentication Configuration

_auth_headers: Optional[Dict[str, str]] = None


def set_auth_headers(headers: Optional[Dict[str, str]]):
    """
    Set authentication headers to be included in all requests.

    Args:
        headers: Dictionary of authentication headers (e.g., {"Authorization": "Bearer token"})
    """
    global _auth_headers
    _auth_headers = headers.copy() if headers else None


def get_auth_headers() -> Dict[str, str]:
    """
    Get authentication headers from configuration or environment variables.

    Supports the following environment variables:
    - A2A_AUTH_TYPE: Type of authentication (bearer, basic, apikey, custom)
    - A2A_AUTH_TOKEN: Token/credential value
    - A2A_AUTH_HEADER: Custom header name (for apikey or custom auth)
    - A2A_AUTH_USERNAME: Username (for basic auth)
    - A2A_AUTH_PASSWORD: Password (for basic auth)

    Returns:
        Dictionary of authentication headers
    """
    global _auth_headers

    # Start with configured headers
    headers = _auth_headers.copy() if _auth_headers else {}

    # Check for environment variable configuration
    auth_type = os.getenv("A2A_AUTH_TYPE", "").lower()

    if auth_type == "bearer":
        # Bearer token authentication
        token = os.getenv("A2A_AUTH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "basic":
        username = os.getenv("A2A_AUTH_USERNAME", "")
        password = os.getenv("A2A_AUTH_PASSWORD", "")
        if username or password:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

    elif auth_type == "apikey":
        # API Key authentication
        token = os.getenv("A2A_AUTH_TOKEN")
        header_name = os.getenv("A2A_AUTH_HEADER", "X-API-Key")
        if token:
            headers[header_name] = token

    elif auth_type == "custom":
        # Custom header authentication
        token = os.getenv("A2A_AUTH_TOKEN")
        header_name = os.getenv("A2A_AUTH_HEADER")
        if token and header_name:
            headers[header_name] = token

    # Allow direct header specification via A2A_AUTH_HEADERS (JSON format)
    auth_headers_json = os.getenv("A2A_AUTH_HEADERS")
    if auth_headers_json:
        try:
            custom_headers = json.loads(auth_headers_json)
            headers.update(custom_headers)
        except (json.JSONDecodeError, ValueError) as e:
            logging.getLogger(__name__).warning(f"Failed to parse A2A_AUTH_HEADERS: {e}")

    return headers


# A2A v0.3.0 Transport Configuration Functions


def set_transport_selection_strategy(strategy: str):
    """
    Set the transport selection strategy.

    Args:
        strategy: Selection strategy ('agent_preferred', 'prefer_jsonrpc',
                 'prefer_grpc', 'prefer_rest', 'all_supported')
    """
    global _transport_selection_strategy
    valid_strategies = {"agent_preferred", "prefer_jsonrpc", "prefer_grpc", "prefer_rest", "all_supported"}
    if strategy not in valid_strategies:
        raise ValueError(f"Invalid transport selection strategy: {strategy}. Valid options: {valid_strategies}")
    _transport_selection_strategy = strategy


def get_transport_selection_strategy() -> str:
    """
    Get the transport selection strategy.

    Returns:
        Current transport selection strategy
    """
    # Check environment variable override
    env_strategy = os.getenv("A2A_TRANSPORT_STRATEGY")
    if env_strategy:
        return env_strategy
    return _transport_selection_strategy


def set_preferred_transport(transport_type: Optional[TransportType]):
    """
    Set a preferred transport type for testing.

    Args:
        transport_type: Preferred transport type or None for auto-selection
    """
    global _preferred_transport
    _preferred_transport = transport_type


def get_preferred_transport() -> Optional[TransportType]:
    """
    Get the preferred transport type.

    Returns:
        Preferred transport type or None if not set
    """
    # Check environment variable override
    env_transport = os.getenv("A2A_PREFERRED_TRANSPORT")
    if env_transport:
        return _parse_transport_from_env(env_transport)
    return _preferred_transport


def set_disabled_transports(transports: List[TransportType]):
    """
    Set list of disabled transport types.

    Args:
        transports: List of transport types to disable
    """
    global _disabled_transports
    _disabled_transports = transports.copy()


def get_disabled_transports() -> List[TransportType]:
    """
    Get list of disabled transport types.

    Returns:
        List of disabled transport types
    """
    # Check environment variable override
    env_disabled = os.getenv("A2A_DISABLED_TRANSPORTS")
    if env_disabled:
        return _parse_transport_list_from_env(env_disabled)
    return _disabled_transports.copy()


def is_transport_enabled(transport_type: TransportType) -> bool:
    """
    Check if a transport type is enabled.

    Args:
        transport_type: Transport type to check

    Returns:
        True if transport is enabled, False if disabled
    """
    return transport_type not in get_disabled_transports()


def set_required_transports(transports: Optional[List[TransportType]]):
    """
    Set list of required transport types for strict selection.

    Args:
        transports: List of required transports, or None for unrestricted
    """
    global _required_transports
    if transports is None:
        _required_transports = None
    else:
        _required_transports = transports.copy()


def get_required_transports() -> Optional[List[TransportType]]:
    """
    Get list of required transport types for strict selection.

    Returns:
        List of required transports, or None if unrestricted
    """
    env_required = os.getenv("A2A_REQUIRED_TRANSPORTS")
    if env_required:
        return _parse_transport_list_from_env(env_required)
    return None if _required_transports is None else _required_transports.copy()


def is_transport_required(transport_type: TransportType) -> bool:
    """
    Check if a transport is within the required set (if any).

    Returns:
        True if no restriction or transport is in required set
    """
    required = get_required_transports()
    return True if required is None else transport_type in required


def set_transport_specific_config(transport_type: TransportType, config: Dict[str, str]):
    """
    Set transport-specific configuration.

    Args:
        transport_type: Transport type to configure
        config: Configuration dictionary
    """
    global _transport_specific_config
    _transport_specific_config[transport_type.value] = config.copy()


def get_transport_specific_config(transport_type: TransportType) -> Dict[str, str]:
    """
    Get transport-specific configuration.

    Args:
        transport_type: Transport type to get config for

    Returns:
        Configuration dictionary for the transport
    """
    config = _transport_specific_config.get(transport_type.value, {}).copy()

    # Add environment variable overrides
    env_prefix = f"A2A_{transport_type.value.upper()}_"
    for key, value in os.environ.items():
        if key.startswith(env_prefix):
            config_key = key[len(env_prefix) :].lower()
            config[config_key] = value

    return config


def set_enable_transport_equivalence_testing(enabled: bool):
    """
    Enable or disable transport equivalence testing.

    Args:
        enabled: True to enable equivalence testing, False to disable
    """
    global _enable_transport_equivalence_testing
    _enable_transport_equivalence_testing = enabled


def get_enable_transport_equivalence_testing() -> bool:
    """
    Check if transport equivalence testing is enabled.

    Returns:
        True if equivalence testing is enabled
    """
    # Check environment variable override
    env_enabled = os.getenv("A2A_ENABLE_EQUIVALENCE_TESTING")
    if env_enabled is not None:
        return env_enabled.lower() in ("true", "1", "yes", "on")
    return _enable_transport_equivalence_testing


def is_transport_equivalence_testing_enabled() -> bool:
    """
    Deprecated: Use get_enable_transport_equivalence_testing() instead.
    """
    return get_enable_transport_equivalence_testing()


def get_transport_capabilities() -> Dict[str, bool]:
    """
    Get transport capability flags from environment.

    Returns:
        Dictionary of capability flags
    """
    return {
        "jsonrpc_enabled": is_transport_enabled(TransportType.JSON_RPC),
        "grpc_enabled": is_transport_enabled(TransportType.GRPC),
        "rest_enabled": is_transport_enabled(TransportType.REST),
        "equivalence_testing_enabled": is_transport_equivalence_testing_enabled(),
        "preferred_transport": get_preferred_transport().value if get_preferred_transport() else None,
        "selection_strategy": get_transport_selection_strategy(),
    }


def _parse_transport_from_env(transport_str: str) -> Optional[TransportType]:
    """
    Parse transport type from environment variable string.

    Args:
        transport_str: Transport string from environment

    Returns:
        TransportType or None if invalid
    """
    transport_map = {
        "jsonrpc": TransportType.JSON_RPC,
        "json-rpc": TransportType.JSON_RPC,
        "grpc": TransportType.GRPC,
        "rest": TransportType.REST,
        "http": TransportType.REST,
    }
    return transport_map.get(transport_str.lower())


def _parse_transport_list_from_env(transport_list_str: str) -> List[TransportType]:
    """
    Parse list of transport types from environment variable.

    Args:
        transport_list_str: Comma-separated transport list

    Returns:
        List of TransportType enums
    """
    transports = []
    for transport_str in transport_list_str.split(","):
        transport_str = transport_str.strip()
        transport = _parse_transport_from_env(transport_str)
        if transport:
            transports.append(transport)
    return transports


def reset_transport_config():
    """
    Reset all transport configuration to defaults.

    Useful for testing and cleanup.
    """
    global _transport_selection_strategy, _preferred_transport
    global _disabled_transports, _required_transports, _transport_specific_config
    global _enable_transport_equivalence_testing, _auth_headers

    _transport_selection_strategy = "agent_preferred"
    _preferred_transport = None
    _disabled_transports = []
    _required_transports = None
    _transport_specific_config = {}
    _enable_transport_equivalence_testing = True
    _auth_headers = None
