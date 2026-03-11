"""Agent card structure validation tests.

Tests the agent card fixture directly for structural compliance
with the A2A specification. No transport operations needed.

Requirements tested:
    CARD-DISC-001, CARD-STRUCT-001, CARD-PROTO-001, CARD-PROTO-002,
    BIND-FIELD-001
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.registry import get_requirement_by_id
from tests.compatibility.markers import core, must


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec
    from tck.validators.json_schema import JSONSchemaValidator


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CARD_DISC_001 = get_requirement_by_id("CARD-DISC-001")
CARD_STRUCT_001 = get_requirement_by_id("CARD-STRUCT-001")
CARD_PROTO_001 = get_requirement_by_id("CARD-PROTO-001")
CARD_PROTO_002 = get_requirement_by_id("CARD-PROTO-002")
BIND_FIELD_001 = get_requirement_by_id("BIND-FIELD-001")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Required top-level fields per the A2A spec (proto REQUIRED annotation).
_REQUIRED_FIELDS = {
    "name",
    "description",
    "version",
    "capabilities",
    "skills",
    "supportedInterfaces",
    "defaultInputModes",
    "defaultOutputModes",
}

_KNOWN_BINDINGS = {"JSONRPC", "GRPC", "HTTP+JSON"}


def _fail_msg(req: RequirementSpec, detail: str) -> str:
    return (
        f"{req.id} [{req.title}]: {detail} (see {req.spec_url})"
    )


def _record(
    collector: Any,
    req: RequirementSpec,
    passed: bool,
    errors: list[str] | None = None,
) -> None:
    collector.record(
        requirement_id=req.id,
        transport="agent_card",
        level=req.level.value,
        passed=passed,
        errors=errors or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@core
class TestAgentCardDiscovery:
    """CARD-DISC-001: Agent card is retrievable."""

    def test_agent_card_retrievable(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Agent card must be retrievable at the well-known URL."""
        req = CARD_DISC_001
        errors = []
        if agent_card is None:
            errors.append("Agent card could not be retrieved")
        elif not isinstance(agent_card, dict):
            errors.append("Agent card is not a JSON object")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))


@must
@core
class TestAgentCardStructure:
    """CARD-STRUCT-001: AgentCard contains required fields and valid structure."""

    def test_agent_card_validates_against_schema(
        self,
        agent_card: dict[str, Any],
        validators: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Agent card must validate against the Agent Card JSON schema."""
        req = CARD_STRUCT_001
        json_validator: JSONSchemaValidator = validators["http_json"]
        result = json_validator.validate(agent_card, "Agent Card")
        _record(collector=compliance_collector, req=req,
                passed=result.valid, errors=result.errors)
        assert result.valid, _fail_msg(req, "; ".join(result.errors))

    def test_required_fields_present(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """All required AgentCard fields must be present."""
        req = CARD_STRUCT_001
        missing = _REQUIRED_FIELDS - agent_card.keys()
        errors = []
        if missing:
            errors.append(f"Missing required fields: {missing}")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))


@must
@core
class TestAgentCardProtocol:
    """CARD-PROTO-001 / CARD-PROTO-002: Protocol declaration."""

    def test_supported_interfaces_non_empty(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """CARD-PROTO-001: supportedInterfaces must be a non-empty list."""
        req = CARD_PROTO_001
        interfaces = agent_card.get("supportedInterfaces")
        errors = []
        if not isinstance(interfaces, list):
            errors.append("supportedInterfaces must be a list")
        elif len(interfaces) == 0:
            errors.append("supportedInterfaces must not be empty")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_each_interface_validates_against_schema(
        self,
        agent_card: dict[str, Any],
        validators: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """CARD-PROTO-002: Each interface must validate against AgentInterface schema."""
        req = CARD_PROTO_002
        interfaces = agent_card.get("supportedInterfaces", [])
        json_validator: JSONSchemaValidator = validators["http_json"]
        errors = []
        for i, iface in enumerate(interfaces):
            result = json_validator.validate(iface, "Agent Interface")
            for err in result.errors:
                errors.append(f"Interface [{i}]: {err}")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))


@must
@core
class TestBindingFieldDeclaration:
    """BIND-FIELD-001: All supported protocols declared in AgentCard."""

    def test_all_protocols_declared(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """All protocols the agent supports must be declared in supportedInterfaces."""
        req = BIND_FIELD_001
        interfaces = agent_card.get("supportedInterfaces", [])
        bindings = {iface.get("protocolBinding") for iface in interfaces}
        unknown = bindings - _KNOWN_BINDINGS
        if unknown:
            pytest.skip(
                f"Agent card declares unknown protocol bindings: {unknown}"
            )
        errors = []
        if len(bindings) < 1:
            errors.append("At least one protocol binding must be declared")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))
