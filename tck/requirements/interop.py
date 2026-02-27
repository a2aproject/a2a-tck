"""Interoperability requirements from A2A specification Section 5.

Covers: Functional equivalence across bindings, field presence,
forward compatibility.
"""

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    AUTH,
    DECLARATION,
    EQUIVALENCE,
    ERROR,
    INTEROP,
    MULTI_OPERATION,
)


INTEROP_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="BIND-EQUIV-001",
        section="5.1",
        title="All supported protocols provide identical functionality",
        level=RequirementLevel.MUST,
        description=(
            "When an agent supports multiple protocols, all supported "
            "protocols MUST provide the same set of operations and "
            "capabilities."
        ),
        expected_behavior="Same operations available across all bindings",
        spec_url=f"{SPEC_BASE}51-functional-equivalence-requirements",
        tags=[INTEROP, EQUIVALENCE, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="BIND-EQUIV-002",
        section="5.1",
        title="All bindings return semantically equivalent results",
        level=RequirementLevel.MUST,
        description=(
            "All supported protocols MUST return semantically equivalent "
            "results for the same requests."
        ),
        expected_behavior="Same request produces equivalent results across bindings",
        spec_url=f"{SPEC_BASE}51-functional-equivalence-requirements",
        tags=[INTEROP, EQUIVALENCE, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="BIND-EQUIV-003",
        section="5.1",
        title="All bindings map errors consistently",
        level=RequirementLevel.MUST,
        description=(
            "All supported protocols MUST map errors consistently using "
            "appropriate protocol-specific codes."
        ),
        expected_behavior="Errors mapped consistently across bindings",
        spec_url=f"{SPEC_BASE}51-functional-equivalence-requirements",
        tags=[INTEROP, EQUIVALENCE, ERROR, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="BIND-EQUIV-004",
        section="5.1",
        title="All bindings support same authentication schemes",
        level=RequirementLevel.MUST,
        description=(
            "All supported protocols MUST support the same authentication "
            "schemes declared in the AgentCard."
        ),
        expected_behavior="Same auth schemes across all bindings",
        spec_url=f"{SPEC_BASE}51-functional-equivalence-requirements",
        tags=[INTEROP, EQUIVALENCE, AUTH, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="BIND-FIELD-001",
        section="5.2",
        title="Agents must declare all supported protocols in AgentCard",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST declare all supported protocols in their AgentCard."
        ),
        expected_behavior="All supported protocols listed in AgentCard",
        spec_url=f"{SPEC_BASE}52-protocol-selection-and-negotiation",
        tags=[INTEROP, DECLARATION],
    ),
]
