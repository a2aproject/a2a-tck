"""Requirements module for A2A protocol specification."""

from tck.requirements.base import (
    OperationType,
    RequirementLevel,
    RequirementSpec,
    TransportBinding,
)
from tck.requirements.registry import (
    ALL_REQUIREMENTS,
    get_cross_cutting_requirements,
    get_may_requirements,
    get_must_requirements,
    get_requirements_by_operation,
    get_requirements_by_section,
    get_requirements_by_tag,
    get_should_requirements,
)


__all__ = [
    "ALL_REQUIREMENTS",
    "OperationType",
    "RequirementLevel",
    "RequirementSpec",
    "TransportBinding",
    "get_cross_cutting_requirements",
    "get_may_requirements",
    "get_must_requirements",
    "get_requirements_by_operation",
    "get_requirements_by_section",
    "get_requirements_by_tag",
    "get_should_requirements",
]
