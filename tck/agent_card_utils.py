"""
Agent Card Utility Module for the A2A TCK.

This module provides utilities for fetching, parsing, and extracting information
from an Agent Card as specified in the A2A Protocol Specification:
https://google.github.io/A2A/specification/#agent-card
"""

import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Union, cast

import requests

logger = logging.getLogger(__name__)

def fetch_agent_card(sut_base_url: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """
    Retrieve the Agent Card JSON from the SUT.
    
    Typically, the Agent Card is available at /.well-known/agent.json relative to the SUT base URL.
    
    Args:
        sut_base_url: The base URL of the SUT
        session: A requests.Session object to use for making the request
    
    Returns:
        The parsed Agent Card JSON as a dictionary, or None if it cannot be retrieved or parsed
    """
    try:
        # Parse the base URL to determine the host
        parsed_url = urllib.parse.urlparse(sut_base_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Construct the agent card URL
        agent_card_url = urllib.parse.urljoin(base_domain, "/.well-known/agent.json")
        
        logger.info(f"Fetching Agent Card from {agent_card_url}")
        response = session.get(agent_card_url, timeout=10)
        response.raise_for_status()
        
        try:
            agent_card = cast(Dict[str, Any], response.json())
            logger.info(f"Successfully retrieved Agent Card: {json.dumps(agent_card)[:200]}...")
            return agent_card
        except ValueError as e:
            logger.error(f"Failed to parse Agent Card JSON: {e}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"HTTP error retrieving Agent Card: {e}")
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
    
    Args:
        agent_card_data: The parsed Agent Card data
    
    Returns:
        A list of authentication scheme objects
    """
    if "authentication" in agent_card_data:
        auth = agent_card_data["authentication"]
        if isinstance(auth, list):
            return auth
    
    # Return empty list if no authentication is declared
    return [] 