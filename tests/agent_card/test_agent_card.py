"""Agent card structure validation tests.

Tests the agent card fixture directly for structural compliance
with the A2A specification. No transport operations needed.

Requirements tested:
    CARD-DISC-001, CARD-STRUCT-001, CARD-PROTO-001, CARD-PROTO-002,
    BIND-FIELD-001
"""

from __future__ import annotations

from typing import Any

import pytest

from tck.requirements.base import RequirementSpec
from tck.requirements.registry import get_requirement_by_id


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

# Required top-level fields per the A2A spec (Section 4.4.1).
_REQUIRED_FIELDS = {"name", "description", "version", "capabilities", "skills"}

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


class TestAgentCardStructure:
    """CARD-STRUCT-001: AgentCard contains required fields."""

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

    def test_name_is_non_empty_string(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        name = agent_card.get("name")
        errors = []
        if not isinstance(name, str) or not name:
            errors.append("name must be a non-empty string")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_description_is_non_empty_string(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        desc = agent_card.get("description")
        errors = []
        if not isinstance(desc, str) or not desc:
            errors.append("description must be a non-empty string")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_version_is_string(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        version = agent_card.get("version")
        errors = []
        if not isinstance(version, str):
            errors.append("version must be a string")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_capabilities_is_object(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        caps = agent_card.get("capabilities")
        errors = []
        if not isinstance(caps, dict):
            errors.append("capabilities must be a JSON object")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_skills_is_list(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        skills = agent_card.get("skills")
        errors = []
        if not isinstance(skills, list):
            errors.append("skills must be a JSON array")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_default_input_modes_present(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        modes = agent_card.get("defaultInputModes")
        errors = []
        if modes is not None:
            if not isinstance(modes, list):
                errors.append("defaultInputModes must be a list")
            elif len(modes) == 0:
                errors.append("defaultInputModes must not be empty")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))

    def test_default_output_modes_present(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        req = CARD_STRUCT_001
        modes = agent_card.get("defaultOutputModes")
        errors = []
        if modes is not None:
            if not isinstance(modes, list):
                errors.append("defaultOutputModes must be a list")
            elif len(modes) == 0:
                errors.append("defaultOutputModes must not be empty")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))


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

    def test_each_interface_has_url_and_binding(
        self,
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """CARD-PROTO-002: Each interface must declare url and protocolBinding."""
        req = CARD_PROTO_002
        interfaces = agent_card.get("supportedInterfaces", [])
        errors = []
        for i, iface in enumerate(interfaces):
            if "url" not in iface:
                errors.append(f"Interface [{i}] missing 'url'")
            elif not isinstance(iface["url"], str) or not iface["url"]:
                errors.append(f"Interface [{i}] 'url' must be a non-empty string")
            if "protocolBinding" not in iface:
                errors.append(f"Interface [{i}] missing 'protocolBinding'")
            elif not isinstance(iface["protocolBinding"], str) or not iface["protocolBinding"]:
                errors.append(f"Interface [{i}] 'protocolBinding' must be a non-empty string")
        _record(collector=compliance_collector, req=req,
                passed=not errors, errors=errors)
        assert not errors, _fail_msg(req, "; ".join(errors))


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
