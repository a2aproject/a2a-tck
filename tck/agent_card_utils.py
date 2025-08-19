"""
Agent Card Utility Module for the A2A TCK v0.3.0.

This module provides utilities for fetching, parsing, and extracting information
from an Agent Card as specified in the A2A Protocol Specification v0.3.0.
Includes support for multi-transport discovery and enhanced security schemes.

Specification Reference: A2A Protocol v0.3.0 §5 - Agent Discovery
"""

import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Union, cast

import requests

from tck.transport.base_client import TransportType

logger = logging.getLogger(__name__)

def fetch_agent_card(sut_base_url: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """
    Retrieve the Agent Card JSON from the SUT.
    
    Tries A2A v0.3.0 location first (/.well-known/agent-card.json), then falls back
    to v0.2.5 location (/.well-known/agent.json) for backward compatibility.
    
    Args:
        sut_base_url: The base URL of the SUT
        session: A requests.Session object to use for making the request
    
    Returns:
        The parsed Agent Card JSON as a dictionary, or None if it cannot be retrieved or parsed
        
    Specification Reference: A2A Protocol v0.3.0 §5.3 - Recommended Location
    """
    # Parse the base URL to determine the host
    parsed_url = urllib.parse.urlparse(sut_base_url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Try v0.3.0 location first
    agent_card_urls = [
        ("/.well-known/agent-card.json", "v0.3.0"),
        ("/.well-known/agent.json", "v0.2.5")  # Backward compatibility
    ]
    
    for url_path, version in agent_card_urls:
        try:
            agent_card_url = urllib.parse.urljoin(base_domain, url_path)
            logger.info(f"Fetching Agent Card from {agent_card_url} ({version} location)")
            
            response = session.get(agent_card_url, timeout=10)
            response.raise_for_status()
            
            try:
                agent_card = cast(Dict[str, Any], response.json())
                logger.info(f"Successfully retrieved Agent Card from {version} location: {json.dumps(agent_card)[:200]}...")
                return agent_card
            except ValueError as e:
                logger.error(f"Failed to parse Agent Card JSON from {agent_card_url}: {e}")
                continue  # Try next location
                
        except requests.RequestException as e:
            logger.info(f"Agent Card not found at {version} location ({url_path}): {e}")
            continue  # Try next location
    
    logger.error("Failed to fetch Agent Card from any known location")
    return None

def get_sut_rpc_endpoint(agent_card_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract the SUT's JSON-RPC endpoint URL from the Agent Card.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        The JSON-RPC endpoint URL, or None if not found
    """
    # The endpoint might be directly in the root of the Agent Card
    if "endpoint" in agent_card_data:
        return cast(str, agent_card_data["endpoint"])
    
    # It might also be in a jsonrpc section or similar
    if "jsonrpc" in agent_card_data and "endpoint" in agent_card_data["jsonrpc"]:
        return cast(str, agent_card_data["jsonrpc"]["endpoint"])
    
    # If we can't find it, return None
    logger.warning("Could not find JSON-RPC endpoint in Agent Card")
    return None

def get_capability_streaming(agent_card_data: Dict[str, Any]) -> bool:
    """
    Check if the SUT supports streaming capabilities.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        True if streaming is supported, False otherwise
    """
    if "capabilities" in agent_card_data:
        capabilities = agent_card_data["capabilities"]
        if isinstance(capabilities, dict) and "streaming" in capabilities:
            return bool(capabilities["streaming"])
    
    # Default to False if not specified
    return False

def get_capability_push_notifications(agent_card_data: Dict[str, Any]) -> bool:
    """
    Check if the SUT supports push notifications.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        True if push notifications are supported, False otherwise
    """
    if "capabilities" in agent_card_data:
        capabilities = agent_card_data["capabilities"]
        if isinstance(capabilities, dict) and "pushNotifications" in capabilities:
            return bool(capabilities["pushNotifications"])
    
    # Default to False if not specified
    return False

def get_supported_modalities(agent_card_data: Dict[str, Any], skill_id: Optional[str] = None) -> List[str]:
    """
    Get the supported modalities (input/output modes) from the Agent Card.
    
    Args:
        agent_card_data: The parsed Agent Card data
        skill_id: Optional skill ID to get modalities for a specific skill
    
    Returns:
        A list of supported modality strings (e.g., ["text", "file", "data"])
    """
    modalities: Set[str] = set()
    
    # Check capabilities.skills section for inputOutputModes
    if "capabilities" in agent_card_data and "skills" in agent_card_data["capabilities"]:
        skills = agent_card_data["capabilities"]["skills"]
        
        if isinstance(skills, list):
            for skill in skills:
                # Skip if we're looking for a specific skill and this isn't it
                if skill_id and skill.get("id") != skill_id:
                    continue
                    
                if "inputOutputModes" in skill:
                    io_modes = skill["inputOutputModes"]
                    if isinstance(io_modes, list):
                        modalities.update(mode for mode in io_modes if isinstance(mode, str))
    
    return list(modalities)

def get_authentication_schemes(agent_card_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get the authentication schemes declared in the Agent Card.
    
    According to the A2A specification, authentication schemes should be defined
    using OpenAPI 3.x Security Scheme objects in the 'securitySchemes' field.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        A list of authentication scheme objects from securitySchemes
    """
    # Look for securitySchemes as per A2A/OpenAPI specification
    if "securitySchemes" in agent_card_data:
        schemes = agent_card_data["securitySchemes"]
        if isinstance(schemes, dict):
            # Convert dict of schemes to list of scheme objects
            return list(schemes.values())
    
    # Fallback: check for legacy 'authentication' field for backward compatibility
    if "authentication" in agent_card_data:
        auth = agent_card_data["authentication"]
        if isinstance(auth, list):
            return auth
    
    # Return empty list if no authentication is declared
    return []


# A2A v0.3.0 Transport Discovery Functions

def get_supported_transports(agent_card_data: Dict[str, Any]) -> List[TransportType]:
    """
    Discover supported transport protocols from the Agent Card.
    
    Extracts transport information from preferredTransport and additionalInterfaces fields.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        List of supported TransportType enums
        
    Specification Reference: A2A Protocol v0.3.0 §3.4.2 - Transport Selection and Negotiation
    """
    supported_transports: Set[TransportType] = set()
    
    # Check preferred transport
    preferred = agent_card_data.get("preferredTransport")
    if preferred and isinstance(preferred, str):
        transport_type = _parse_transport_type(preferred)
        if transport_type:
            supported_transports.add(transport_type)
    
    # Check additional interfaces
    additional = agent_card_data.get("additionalInterfaces", [])
    if isinstance(additional, list):
        for interface in additional:
            if isinstance(interface, dict):
                transport_name = interface.get("transport") or interface.get("type")
                if transport_name and isinstance(transport_name, str):
                    transport_type = _parse_transport_type(transport_name)
                    if transport_type:
                        supported_transports.add(transport_type)
    
    return list(supported_transports)


def get_preferred_transport(agent_card_data: Dict[str, Any]) -> Optional[TransportType]:
    """
    Get the preferred transport protocol from the Agent Card.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        The preferred TransportType, or None if not specified
        
    Specification Reference: A2A Protocol v0.3.0 §3.4.2 - Transport Selection and Negotiation
    """
    preferred = agent_card_data.get("preferredTransport")
    if preferred and isinstance(preferred, str):
        return _parse_transport_type(preferred)
    return None


def get_transport_endpoints(agent_card_data: Dict[str, Any]) -> Dict[TransportType, str]:
    """
    Extract transport-specific endpoints from the Agent Card.
    
    Maps each supported transport to its corresponding endpoint URL.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        Dictionary mapping TransportType to endpoint URL
        
    Specification Reference: A2A Protocol v0.3.0 §3.1 - Transport Layer Requirements
    """
    endpoints: Dict[TransportType, str] = {}
    
    # Check for main endpoint (usually JSON-RPC)
    main_endpoint = agent_card_data.get("endpoint")
    if main_endpoint and isinstance(main_endpoint, str):
        # Assume main endpoint is JSON-RPC unless specified otherwise
        endpoints[TransportType.JSON_RPC] = main_endpoint
    else:
        # Fallback: check main "url" field and map to preferred transport
        main_url = agent_card_data.get("url")
        preferred_transport = agent_card_data.get("preferredTransport")
        if main_url and isinstance(main_url, str) and preferred_transport and isinstance(preferred_transport, str):
            transport_type = _parse_transport_type(preferred_transport)
            if transport_type:
                endpoints[transport_type] = main_url
    
    # Check additional interfaces for transport-specific endpoints
    additional = agent_card_data.get("additionalInterfaces", [])
    if isinstance(additional, list):
        for interface in additional:
            if isinstance(interface, dict):
                transport_name = interface.get("transport") or interface.get("type")
                endpoint = interface.get("endpoint") or interface.get("url")
                
                if transport_name and endpoint and isinstance(transport_name, str) and isinstance(endpoint, str):
                    transport_type = _parse_transport_type(transport_name)
                    if transport_type:
                        endpoints[transport_type] = endpoint
    
    return endpoints


def get_transport_interface_info(agent_card_data: Dict[str, Any], transport_type: TransportType) -> Optional[Dict[str, Any]]:
    """
    Get detailed interface information for a specific transport.
    
    Args:
        agent_card_data: The parsed Agent Card data
        transport_type: The transport type to get information for
    
    Returns:
        Interface information dictionary, or None if not found
        
    Specification Reference: A2A Protocol v0.3.0 §3.2 - Supported Transport Protocols
    """
    # Check if this is the preferred transport with main endpoint
    preferred = get_preferred_transport(agent_card_data)
    if preferred == transport_type:
        endpoint = agent_card_data.get("endpoint")
        if endpoint:
            return {
                "transport": transport_type.value,
                "endpoint": endpoint,
                "preferred": True
            }
    
    # Check additional interfaces
    additional = agent_card_data.get("additionalInterfaces", [])
    if isinstance(additional, list):
        for interface in additional:
            if isinstance(interface, dict):
                transport_name = interface.get("transport") or interface.get("type")
                if transport_name and _parse_transport_type(transport_name) == transport_type:
                    return interface
    
    return None


def _parse_transport_type(transport_name: str) -> Optional[TransportType]:
    """
    Parse a transport name string to TransportType enum.
    
    Handles various naming conventions for transport types.
    
    Args:
        transport_name: String representation of transport type
    
    Returns:
        Corresponding TransportType enum or None if not recognized
    """
    normalized = transport_name.lower().strip()
    
    # JSON-RPC variants
    if normalized in ["jsonrpc", "json-rpc", "jsonrpc2.0", "json-rpc-2.0", "rpc"]:
        return TransportType.JSON_RPC
    
    # gRPC variants  
    if normalized in ["grpc", "grpc-web", "protobuf"]:
        return TransportType.GRPC
    
    # REST variants
    if normalized in ["rest", "http", "http+json", "restful", "http-json"]:
        return TransportType.REST
    
    return None


def has_transport_support(agent_card_data: Dict[str, Any], transport_type: TransportType) -> bool:
    """
    Check if the agent supports a specific transport type.
    
    Args:
        agent_card_data: The parsed Agent Card data
        transport_type: The transport type to check for
    
    Returns:
        True if the transport is supported, False otherwise
        
    Specification Reference: A2A Protocol v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    supported_transports = get_supported_transports(agent_card_data)
    return transport_type in supported_transports


def validate_transport_consistency(agent_card_data: Dict[str, Any]) -> List[str]:
    """
    Validate that transport declarations are consistent and complete.
    
    Checks for common issues in transport configuration.
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        List of validation error messages (empty if valid)
        
    Specification Reference: A2A Protocol v0.3.0 §3.4 - Transport Compliance and Interoperability
    """
    errors: List[str] = []
    
    # Check that at least one transport is declared
    supported_transports = get_supported_transports(agent_card_data)
    if not supported_transports:
        errors.append("No supported transports declared in Agent Card")
        return errors  # Can't validate further without transports
    
    # Check that all declared transports have endpoints
    endpoints = get_transport_endpoints(agent_card_data)
    for transport in supported_transports:
        if transport not in endpoints:
            errors.append(f"Transport {transport.value} declared but no endpoint provided")
    
    # Check for orphaned endpoints (endpoints without transport declarations)
    additional = agent_card_data.get("additionalInterfaces", [])
    if isinstance(additional, list):
        for interface in additional:
            if isinstance(interface, dict):
                transport_name = interface.get("transport") or interface.get("type")
                if transport_name:
                    transport_type = _parse_transport_type(transport_name)
                    if not transport_type:
                        errors.append(f"Unknown transport type in additionalInterfaces: {transport_name}")
    
    return errors