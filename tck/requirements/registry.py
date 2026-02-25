"""Requirement registry for A2A protocol specification requirements.

This module provides a central registry for all ~100 requirement definitions
that will be tested by the TCK. The actual requirements will be populated
in Phase 4.

Reference: PRD Section 5.1.3 (Requirement Registry)
"""

from tck.requirements.base import (
    OperationType,
    RequirementLevel,
    RequirementSpec,
)


# Will be populated in Phase 4
ALL_REQUIREMENTS: list[RequirementSpec] = []


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
