"""Parametrized requirement tests for A2A protocol conformance.

Tests are grouped by RFC 2119 requirement level (MUST/SHOULD/MAY) and
parametrized across all transports and all registered requirements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.registry import (
    get_may_requirements,
    get_must_requirements,
    get_should_requirements,
)
from tck.transport import ALL_TRANSPORTS
from tck.transport.base import StreamingResponse
from tck.transport.dispatch import execute_operation
from tck.validators.error_binding import validate_expected_error
from tck.validators.streaming import validate_streaming_events
from tests.compatibility.markers import may, must, should


# Maps requirement tags to agent card capability keys.
# When a requirement's tags include one of these keys and the corresponding
# capability is not declared in the agent card, the test is skipped.
_CAPABILITY_TAG_TO_CARD_KEY = {
    "streaming": "streaming",
    "push-notification": "pushNotifications",
    "agent-card": "extendedAgentCard",
}


def _skip_if_capability_not_declared(
    requirement: Any,
    transport: str,
    agent_card: dict[str, Any],
    compatibility_collector: Any,
) -> None:
    """Skip the test if the requirement needs a capability not declared in the agent card."""
    if not requirement.tags:
        return
    card_caps = agent_card.get("capabilities") or {}
    missing = [
        t for t in requirement.tags
        if t in _CAPABILITY_TAG_TO_CARD_KEY and not card_caps.get(_CAPABILITY_TAG_TO_CARD_KEY[t])
    ]
    if missing:
        compatibility_collector.record(
            requirement_id=requirement.id,
            transport=transport,
            level=requirement.level.value,
            passed=False,
            skipped=True,
        )
        pytest.skip(
            f"Agent card does not declare capabilities for: {missing}"
        )


if TYPE_CHECKING:
    from collections.abc import Callable

    from tck.requirements.base import RequirementSpec


def _parametrize_requirements(
    getter: Callable[[], list[RequirementSpec]],
) -> list[pytest.param]:
    """Return pytest.param list from a requirement getter, handling empty lists.

    Requirements without an ``operation`` or tagged ``multi-operation``
    are excluded because the parametrized runner cannot dispatch them.
    Cross-cutting and multi-operation requirements are covered by
    dedicated test modules (e.g. ``test_task_lifecycle``).
    """
    reqs = [
        r for r in getter()
        if r.operation is not None and "multi-operation" not in r.tags
    ]
    if not reqs:
        return [pytest.param(None, id="no-requirements",
                             marks=pytest.mark.skip(reason="No requirements at this level"))]
    return [pytest.param(r, id=r.id) for r in reqs]



def _validate_response(
    response: Any,
    transport: str,
    requirement: Any,
    validators: dict[str, Any],
) -> list[str]:
    """Validate a transport response and return a list of error strings."""
    errors: list[str] = []

    # Requirements that expect a specific error
    if requirement.expected_error is not None:
        return validate_expected_error(response, transport, requirement.expected_error)

    # For streaming responses, just verify at least one event arrives
    if isinstance(response, StreamingResponse):
        if not response.success:
            errors.append(f"Streaming operation failed: {response.error}")
        else:
            errors.extend(validate_streaming_events(response))
        return errors

    # Non-streaming: check success flag
    if not response.success:
        errors.append(f"Operation failed: {response.error}")
        return errors

    # Schema validation when a schema ref is available
    schema_ref = requirement.json_schema_ref or requirement.proto_response_type
    if schema_ref and transport in ("jsonrpc", "http_json"):
        validator = validators.get(transport)
        if validator is not None:
            result = validator.validate(response.raw_response, schema_ref)
            if not result.valid:
                errors.extend(result.errors)

    # Custom content validation
    for validator in requirement.validators:
        errors.extend(validator(response, transport))

    return errors


def _format_failure(
    requirement: Any,
    transport: str,
    errors: list[str],
) -> str:
    """Build a human-readable failure message."""
    joined = "; ".join(errors)
    return (
        f"{requirement.id} [{requirement.title}] failed on {transport}: "
        f"{joined} (see {requirement.spec_url})"
    )


# ---------------------------------------------------------------------------
# MUST requirements — hard failure
# ---------------------------------------------------------------------------

@must
@pytest.mark.parametrize(
    "transport",
    ALL_TRANSPORTS,
)
@pytest.mark.parametrize(
    "requirement",
    _parametrize_requirements(get_must_requirements),
)
def test_must_requirement(
    transport: str,
    requirement: Any,
    transport_clients: dict[str, Any],
    validators: dict[str, Any],
    compatibility_collector: Any,
    agent_card: dict[str, Any],
) -> None:
    """Verify a MUST-level requirement — hard failure on validation error."""
    _skip_if_capability_not_declared(requirement, transport, agent_card, compatibility_collector)
    client = transport_clients.get(transport)
    if client is None:
        compatibility_collector.record(
            requirement_id=requirement.id,
            transport=transport,
            level=requirement.level.value,
            passed=False,
            skipped=True,
        )
        pytest.skip(f"Transport {transport!r} not configured (filtered by --transport)")

    response = execute_operation(client, requirement)
    errors = _validate_response(response, transport, requirement, validators)

    compatibility_collector.record(
        requirement_id=requirement.id,
        transport=transport,
        level=requirement.level.value,
        passed=len(errors) == 0,
        errors=errors,
    )

    assert not errors, _format_failure(requirement, transport, errors)


# ---------------------------------------------------------------------------
# SHOULD requirements — expected failure (xfail), not hard fail
# ---------------------------------------------------------------------------

@should
@pytest.mark.parametrize(
    "transport",
    ALL_TRANSPORTS,
)
@pytest.mark.parametrize(
    "requirement",
    _parametrize_requirements(get_should_requirements),
)
def test_should_requirement(
    transport: str,
    requirement: Any,
    transport_clients: dict[str, Any],
    validators: dict[str, Any],
    compatibility_collector: Any,
    agent_card: dict[str, Any],
) -> None:
    """Verify a SHOULD-level requirement — xfail on validation error."""
    _skip_if_capability_not_declared(requirement, transport, agent_card, compatibility_collector)
    client = transport_clients.get(transport)
    if client is None:
        compatibility_collector.record(
            requirement_id=requirement.id,
            transport=transport,
            level=requirement.level.value,
            passed=False,
            skipped=True,
        )
        pytest.skip(f"Transport {transport!r} not configured (filtered by --transport)")

    response = execute_operation(client, requirement)
    errors = _validate_response(response, transport, requirement, validators)

    compatibility_collector.record(
        requirement_id=requirement.id,
        transport=transport,
        level=requirement.level.value,
        passed=len(errors) == 0,
        errors=errors,
    )

    if errors:
        pytest.xfail(_format_failure(requirement, transport, errors))


# ---------------------------------------------------------------------------
# MAY requirements — skip if capability not declared in agent card
# ---------------------------------------------------------------------------

@may
@pytest.mark.parametrize(
    "transport",
    ALL_TRANSPORTS,
)
@pytest.mark.parametrize(
    "requirement",
    _parametrize_requirements(get_may_requirements),
)
def test_may_requirement(
    transport: str,
    requirement: Any,
    transport_clients: dict[str, Any],
    validators: dict[str, Any],
    compatibility_collector: Any,
    agent_card: dict[str, Any],
) -> None:
    """Verify a MAY-level requirement — skip if capability not declared."""
    _skip_if_capability_not_declared(requirement, transport, agent_card, compatibility_collector)
    client = transport_clients.get(transport)
    if client is None:
        compatibility_collector.record(
            requirement_id=requirement.id,
            transport=transport,
            level=requirement.level.value,
            passed=False,
            skipped=True,
        )
        pytest.skip(f"Transport {transport!r} not configured (filtered by --transport)")

    response = execute_operation(client, requirement)
    errors = _validate_response(response, transport, requirement, validators)

    compatibility_collector.record(
        requirement_id=requirement.id,
        transport=transport,
        level=requirement.level.value,
        passed=len(errors) == 0,
        errors=errors,
    )

    if errors:
        pytest.xfail(_format_failure(requirement, transport, errors))
