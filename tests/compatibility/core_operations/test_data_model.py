"""Data model compliance tests via schema validation.

Sends a single SendMessage per transport, then validates the response
against the A2A JSON Schema and protobuf definitions.

Requirements tested:
    DM-TASK-001, DM-TASK-002, DM-MSG-001, DM-MSG-002, DM-PART-001,
    DM-ART-001, DM-STATUS-001, DM-SERIAL-001, DM-SERIAL-002,
    DM-SERIAL-003, DM-SERIAL-004
"""

from __future__ import annotations

import re

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.registry import get_requirement_by_id
from tests.compatibility._test_helpers import fail_msg, record
from tests.compatibility.markers import core, must


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

DM_TASK_001 = get_requirement_by_id("DM-TASK-001")
DM_TASK_002 = get_requirement_by_id("DM-TASK-002")
DM_MSG_001 = get_requirement_by_id("DM-MSG-001")
DM_MSG_002 = get_requirement_by_id("DM-MSG-002")
DM_PART_001 = get_requirement_by_id("DM-PART-001")
DM_ART_001 = get_requirement_by_id("DM-ART-001")
DM_STATUS_001 = get_requirement_by_id("DM-STATUS-001")
DM_SERIAL_001 = get_requirement_by_id("DM-SERIAL-001")
DM_SERIAL_002 = get_requirement_by_id("DM-SERIAL-002")
DM_SERIAL_003 = get_requirement_by_id("DM-SERIAL-003")
DM_SERIAL_004 = get_requirement_by_id("DM-SERIAL-004")

# snake_case detector for DM-SERIAL-001
_SNAKE_CASE_PATTERN = re.compile(r"^[a-z]+(_[a-z]+)+$")

# ISO 8601 with Z suffix for DM-SERIAL-003
_ISO_8601_Z_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)

_SAMPLE_MESSAGE = {
    "role": "ROLE_USER",
    "parts": [{"text": "Hello from TCK data model test"}],
    "messageId": "tck-dm-test-001",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_result(raw: Any) -> dict | None:
    """Extract the result payload (unwrap JSON-RPC envelope if present)."""
    if isinstance(raw, dict):
        if "result" in raw:
            return raw["result"]
        return raw
    return None


def _collect_keys_recursive(obj: Any, keys: set[str]) -> None:
    """Recursively collect all dict keys."""
    if isinstance(obj, dict):
        keys.update(obj.keys())
        for v in obj.values():
            _collect_keys_recursive(v, keys)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys_recursive(item, keys)


def _collect_values_for_key(obj: Any, key: str, values: list[Any]) -> None:
    """Recursively collect all values for a given key."""
    if isinstance(obj, dict):
        if key in obj:
            values.append(obj[key])
        for v in obj.values():
            _collect_values_for_key(v, key, values)
    elif isinstance(obj, list):
        for item in obj:
            _collect_values_for_key(item, key, values)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def send_message_responses(
    transport_clients: dict[str, BaseTransportClient],
) -> dict[str, Any]:
    """Send a message on each transport and cache the raw responses."""
    responses: dict[str, Any] = {}
    for transport_name, client in transport_clients.items():
        # gRPC handles serialization differently; skip for JSON-level tests
        if transport_name == "grpc":
            continue
        response = client.send_message(message=_SAMPLE_MESSAGE)
        if response.success and response.raw_response is not None:
            responses[transport_name] = response.raw_response
    return responses


# ---------------------------------------------------------------------------
# Schema-validated tests (DM-TASK-001 .. DM-ART-001, DM-STATUS-001)
# ---------------------------------------------------------------------------


@must
@core
class TestSendMessageResponseSchema:
    """DM-TASK-001 through DM-STATUS-001: Validate response against JSON schema.

    A single schema validation of the SendMessageResponse covers:
    - DM-TASK-001: Task required fields (id, status)
    - DM-TASK-002: TaskState enum values
    - DM-MSG-001: Message required fields (role, parts, messageId)
    - DM-MSG-002: Role enum values
    - DM-PART-001: Part oneof semantics
    - DM-ART-001: Artifact required fields
    - DM-STATUS-001: TaskStatus.state field
    - DM-SERIAL-004: Required fields present
    """

    # Map each requirement to the schema definition it checks.
    _REQ_SCHEMA_PAIRS: list[tuple[RequirementSpec, str]] = [
        (DM_TASK_001, "Send Message Response"),
        (DM_TASK_002, "Send Message Response"),
        (DM_MSG_001, "Send Message Response"),
        (DM_MSG_002, "Send Message Response"),
        (DM_PART_001, "Send Message Response"),
        (DM_ART_001, "Send Message Response"),
        (DM_STATUS_001, "Send Message Response"),
        (DM_SERIAL_004, "Send Message Response"),
    ]

    def test_response_validates_against_schema(
        self,
        send_message_responses: dict[str, Any],
        validators: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Validate each response against the SendMessageResponse JSON schema."""
        if not send_message_responses:
            pytest.skip("No successful send_message responses")

        for transport, raw in send_message_responses.items():
            validator = validators.get(transport)
            if validator is None:
                continue

            result = validator.validate(raw, "Send Message Response")

            for req, _schema_ref in self._REQ_SCHEMA_PAIRS:
                record(
                    collector=compliance_collector,
                    req=req,
                    transport=transport,
                    passed=result.valid,
                    errors=result.errors if not result.valid else [],
                )

            assert result.valid, fail_msg(
                DM_TASK_001, transport,
                f"Schema validation failed: {'; '.join(result.errors)}",
            )


# ---------------------------------------------------------------------------
# Serialization convention tests (DM-SERIAL-001 .. DM-SERIAL-003)
#
# These check cross-cutting serialization rules that the JSON schema
# cannot enforce (naming convention, enum encoding, timestamp format).
# ---------------------------------------------------------------------------


@must
@core
class TestCamelCaseFieldNames:
    """DM-SERIAL-001: JSON serialization uses camelCase field names."""

    def test_no_snake_case_keys(
        self,
        send_message_responses: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Field names must use camelCase, not snake_case."""
        req = DM_SERIAL_001
        if not send_message_responses:
            pytest.skip("No successful send_message responses")
        for transport, raw in send_message_responses.items():
            keys: set[str] = set()
            _collect_keys_recursive(raw, keys)
            snake_case_keys = {k for k in keys if _SNAKE_CASE_PATTERN.match(k)}
            errors = []
            if snake_case_keys:
                errors.append(f"Found snake_case field names: {snake_case_keys}")
            record(collector=compliance_collector, req=req, transport=transport,
                    passed=not errors, errors=errors)
            assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@core
class TestEnumSerialization:
    """DM-SERIAL-002: Enum values are strings, not integers."""

    def test_enum_values_are_strings(
        self,
        send_message_responses: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Enum values must be serialized as strings, not integers."""
        req = DM_SERIAL_002
        if not send_message_responses:
            pytest.skip("No successful send_message responses")
        for transport, raw in send_message_responses.items():
            errors = []
            for key in ("state", "role"):
                values: list[Any] = []
                _collect_values_for_key(raw, key, values)
                for val in values:
                    if not isinstance(val, str):
                        errors.append(
                            f"Enum '{key}' must be a string, got "
                            f"{type(val).__name__}: {val!r}"
                        )
            record(collector=compliance_collector, req=req, transport=transport,
                    passed=not errors, errors=errors)
            assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@core
class TestTimestampFormat:
    """DM-SERIAL-003: Timestamps use ISO 8601 format with Z suffix."""

    _TIMESTAMP_KEYS = {"timestamp", "createdAt", "updatedAt", "statusTimestamp"}

    def test_timestamps_are_iso8601_utc(
        self,
        send_message_responses: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Timestamps must use ISO 8601 format with Z suffix."""
        req = DM_SERIAL_003
        if not send_message_responses:
            pytest.skip("No successful send_message responses")
        found_timestamp = False
        for transport, raw in send_message_responses.items():
            errors = []
            for key in self._TIMESTAMP_KEYS:
                timestamps: list[Any] = []
                _collect_values_for_key(raw, key, timestamps)
                for ts in timestamps:
                    if ts is None:
                        continue
                    found_timestamp = True
                    if not isinstance(ts, str):
                        errors.append(f"Timestamp '{key}' must be a string")
                    elif not _ISO_8601_Z_PATTERN.match(ts):
                        errors.append(
                            f"Timestamp '{key}' must be ISO 8601 with Z suffix, "
                            f"got: {ts!r}"
                        )
            record(collector=compliance_collector, req=req, transport=transport,
                    passed=not errors, errors=errors)
            assert not errors, fail_msg(req, transport, "; ".join(errors))
        if not found_timestamp:
            pytest.skip("No timestamps found in responses to validate")
