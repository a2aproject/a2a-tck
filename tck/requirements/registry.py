"""Requirement registry for A2A protocol specification requirements.

This module provides a central registry for all requirement definitions
that will be tested by the TCK.

Reference: PRD Section 5.1.3 (Requirement Registry)
"""

from tck.requirements.agent_card import AGENT_CARD_REQUIREMENTS
from tck.requirements.auth import AUTH_REQUIREMENTS
from tck.requirements.base import (
    OperationType,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.binding_grpc import BINDING_GRPC_REQUIREMENTS
from tck.requirements.binding_jsonrpc import BINDING_JSONRPC_REQUIREMENTS
from tck.requirements.binding_rest import BINDING_REST_REQUIREMENTS
from tck.requirements.core_operations import CORE_OPERATIONS_REQUIREMENTS
from tck.requirements.data_model import DATA_MODEL_REQUIREMENTS
from tck.requirements.interop import INTEROP_REQUIREMENTS
from tck.requirements.push_notifications import PUSH_NOTIFICATION_REQUIREMENTS
from tck.requirements.streaming import STREAMING_REQUIREMENTS
from tck.requirements.versioning import VERSIONING_REQUIREMENTS


ALL_REQUIREMENTS: list[RequirementSpec] = [
    *CORE_OPERATIONS_REQUIREMENTS,
    *DATA_MODEL_REQUIREMENTS,
    *STREAMING_REQUIREMENTS,
    *PUSH_NOTIFICATION_REQUIREMENTS,
    *AGENT_CARD_REQUIREMENTS,
    *AUTH_REQUIREMENTS,
    *VERSIONING_REQUIREMENTS,
    *INTEROP_REQUIREMENTS,
    *BINDING_JSONRPC_REQUIREMENTS,
    *BINDING_GRPC_REQUIREMENTS,
    *BINDING_REST_REQUIREMENTS,
]

# Import-time duplicate ID validation
_seen_ids: set[str] = set()
for _req in ALL_REQUIREMENTS:
    if _req.id in _seen_ids:
        raise ValueError(f"Duplicate requirement ID: {_req.id}")
    _seen_ids.add(_req.id)
del _seen_ids, _req


# Filtered views
def get_must_requirements() -> list[RequirementSpec]:
    """Get all MUST-level requirements."""
    return [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MUST]


def get_should_requirements() -> list[RequirementSpec]:
    """Get all SHOULD-level requirements."""
    return [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.SHOULD]


def get_may_requirements() -> list[RequirementSpec]:
    """Get all MAY-level requirements."""
    return [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MAY]


# Convenience aliases (computed on access)
MUST_REQUIREMENTS = property(get_must_requirements)
SHOULD_REQUIREMENTS = property(get_should_requirements)
MAY_REQUIREMENTS = property(get_may_requirements)


# Helper functions
def get_requirements_by_section(section_prefix: str) -> list[RequirementSpec]:
    """Get all requirements for a section.

    Args:
        section_prefix: The section prefix to filter by (e.g., '3.1').

    Returns:
        List of requirements whose section starts with the given prefix.
    """
    return [r for r in ALL_REQUIREMENTS if r.section.startswith(section_prefix)]


def get_requirements_by_operation(operation: OperationType) -> list[RequirementSpec]:
    """Get all requirements for an operation type.

    Args:
        operation: The operation type to filter by.

    Returns:
        List of requirements for the specified operation.
    """
    return [r for r in ALL_REQUIREMENTS if r.operation == operation]


def get_requirements_by_tag(tag: str) -> list[RequirementSpec]:
    """Get all requirements with a specific tag.

    Args:
        tag: The tag to filter by.

    Returns:
        List of requirements that have the specified tag.
    """
    return [r for r in ALL_REQUIREMENTS if tag in r.tags]


def get_cross_cutting_requirements() -> list[RequirementSpec]:
    """Get all cross-cutting requirements (not tied to a specific operation).

    Returns:
        List of requirements where operation is None.
    """
    return [r for r in ALL_REQUIREMENTS if r.operation is None]


# Pre-built index for O(1) lookups by requirement ID.
_REQUIREMENTS_BY_ID: dict[str, RequirementSpec] = {r.id: r for r in ALL_REQUIREMENTS}


def get_requirement_by_id(req_id: str) -> RequirementSpec:
    """Look up a requirement by its unique ID.

    Args:
        req_id: The requirement ID (e.g. ``"CORE-ERR-001"``).

    Returns:
        The matching :class:`RequirementSpec`.

    Raises:
        KeyError: If no requirement with that ID exists.
    """
    return _REQUIREMENTS_BY_ID[req_id]
