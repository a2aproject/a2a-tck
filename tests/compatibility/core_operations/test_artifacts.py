"""Opt-in reference-SUT fixture contracts, not RFC 2119 requirements.

Protocol shape is independently exercised by test_data_model.py. When an
operator opts into a fixture, validate the actual response before checking its
reference-specific content. Fixture results belong to pytest/JUnit, not the
protocol compatibility score.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import TASK_STATE_INPUT_REQUIRED, tck_id
from tck.transport import ALL_TRANSPORTS
from tck.validators import SEND_MESSAGE_RESPONSE
from tck.validators.observed_response import observed_checks
from tck.validators.payload import (
    extract_artifacts,
    extract_message,
    get_artifact_id,
    get_artifact_parts,
    get_part_data,
    get_part_filename,
    get_part_media_type,
    get_part_text,
    get_part_type,
    validate_artifact_structure,
    validate_task_state,
)
from tests.compatibility._test_helpers import get_client


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _send_and_get_response(
    client: BaseTransportClient,
    prefix: str,
    transport: str,
    validators: dict[str, Any],
) -> Any:
    """Require a valid successful reply to the declared reference input."""
    message: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK artifact test"}],
        "messageId": tck_id(prefix),
    }
    response = client.send_message(message=message)
    if not response.success:
        pytest.fail(f"{prefix}: send_message failed: {response.error}")
    shape = validators[transport].validate(response.raw_response, SEND_MESSAGE_RESPONSE)
    assert shape.valid, f"{prefix}: invalid response: {shape.errors}"
    errors = [e for findings in observed_checks(response.raw_response, transport).values() for e in findings]
    assert not errors, f"{prefix}: invalid response: {errors}"
    if not validate_task_state(response, transport, TASK_STATE_INPUT_REQUIRED):
        pytest.fail(f"{prefix}: INPUT_REQUIRED is a protocol state, not the promised fixture output")
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.reference_scenario("artifact-text")
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestTextArtifact:
    """DM-ART-001 / DM-PART-001: Task with a text artifact."""

    def test_task_has_text_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        validators: dict[str, Any],
    ) -> None:
        """Response contains an artifact with a TextPart."""
        client = get_client(transport_clients, transport)
        response = _send_and_get_response(client, "artifact-text", transport, validators)

        errors, part = validate_artifact_structure(response, transport, "text")
        if part is not None:
            text = get_part_text(part, transport)
            if text != "Generated text content":
                errors.append(
                    f"Expected text 'Generated text content', got {text!r}"
                )

        assert not errors, "; ".join(errors)


@pytest.mark.reference_scenario("artifact-file")
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestFileArtifact:
    """DM-ART-001 / DM-PART-001: Task with a file artifact."""

    def test_task_has_file_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        validators: dict[str, Any],
    ) -> None:
        """Response contains an artifact with a FilePart."""
        client = get_client(transport_clients, transport)
        response = _send_and_get_response(client, "artifact-file", transport, validators)

        # File parts use "raw" (bytes) or "url" (string) content variant
        errors: list[str] = []
        artifacts = extract_artifacts(response, transport)
        if not artifacts:
            errors.append("Response contains no artifacts")
        else:
            artifact = artifacts[0]
            aid = get_artifact_id(artifact, transport)
            if not aid:
                errors.append("Artifact is missing artifactId")

            parts = get_artifact_parts(artifact, transport)
            if not parts:
                errors.append("Artifact has no parts")
            else:
                part = parts[0]
                part_type = get_part_type(part, transport)
                if part_type not in ("raw", "url"):
                    errors.append(
                        f"Expected file part (raw or url), got '{part_type}'"
                    )
                filename = get_part_filename(part, transport)
                if filename != "output.txt":
                    errors.append(
                        f"Expected filename 'output.txt', got {filename!r}"
                    )
                media_type = get_part_media_type(part, transport)
                if media_type != "text/plain":
                    errors.append(
                        f"Expected mediaType 'text/plain', got {media_type!r}"
                    )

        assert not errors, "; ".join(errors)


@pytest.mark.reference_scenario("artifact-file-url")
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestFileUrlArtifact:
    """DM-ART-001 / DM-PART-001: Task with a file URL artifact."""

    def test_task_has_file_url_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        validators: dict[str, Any],
    ) -> None:
        """Response contains an artifact with a FilePart using a URL."""
        client = get_client(transport_clients, transport)
        response = _send_and_get_response(client, "artifact-file-url", transport, validators)

        errors: list[str] = []
        artifacts = extract_artifacts(response, transport)
        if not artifacts:
            errors.append("Response contains no artifacts")
        else:
            artifact = artifacts[0]
            aid = get_artifact_id(artifact, transport)
            if not aid:
                errors.append("Artifact is missing artifactId")

            parts = get_artifact_parts(artifact, transport)
            if not parts:
                errors.append("Artifact has no parts")
            else:
                part = parts[0]
                part_type = get_part_type(part, transport)
                if part_type != "url":
                    errors.append(
                        f"Expected file URL part (url), got '{part_type}'"
                    )
                filename = get_part_filename(part, transport)
                if filename != "output.txt":
                    errors.append(
                        f"Expected filename 'output.txt', got {filename!r}"
                    )
                media_type = get_part_media_type(part, transport)
                if media_type != "text/plain":
                    errors.append(
                        f"Expected mediaType 'text/plain', got {media_type!r}"
                    )

        assert not errors, "; ".join(errors)


@pytest.mark.reference_scenario("artifact-data")
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestDataArtifact:
    """DM-ART-001 / DM-PART-001: Task with a data artifact."""

    def test_task_has_data_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        validators: dict[str, Any],
    ) -> None:
        """Response contains an artifact with a DataPart."""
        client = get_client(transport_clients, transport)
        response = _send_and_get_response(client, "artifact-data", transport, validators)

        errors, part = validate_artifact_structure(response, transport, "data")
        if part is not None:
            data = get_part_data(part, transport)
            expected = {"key": "value", "count": 42}
            if data != expected:
                errors.append(
                    f"Expected data {expected!r}, got {data!r}"
                )

        assert not errors, "; ".join(errors)


@pytest.mark.reference_scenario("message-response")
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestMessageResponse:
    """DM-MSG-001: SendMessage returns a Message (not a Task)."""

    def test_returns_message_with_text_part(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        validators: dict[str, Any],
    ) -> None:
        """Response is a Message with a TextPart."""
        client = get_client(transport_clients, transport)
        response = _send_and_get_response(client, "message-response", transport, validators)

        errors: list[str] = []
        message = extract_message(response, transport)
        if message is None:
            errors.append(
                "Expected a Message response, but got a Task or no payload"
            )
        else:
            # Validate parts
            parts = (
                list(message.parts)
                if transport == "grpc"
                else message.get("parts", []) if isinstance(message, dict) else []
            )

            if not parts:
                errors.append("Message has no parts")
            else:
                part = parts[0]
                text = get_part_text(part, transport)
                if text != "Direct message response":
                    errors.append(
                        f"Expected text 'Direct message response', got {text!r}"
                    )

        assert not errors, "; ".join(errors)
