"""Artifact and Part content validation tests.

Sends messages that trigger specific artifact/part types in the SUT
and validates the response contains the expected content.

Requirements tested:
    DM-PART-001 — Part uses oneof semantics (text, file, or data)
    DM-ART-001  — Artifact contains required fields (artifactId, parts)
    DM-MSG-001  — Message contains required fields (role, parts, messageId)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
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
)
from tests.compatibility._test_helpers import assert_and_record, get_client
from tests.compatibility.markers import core, must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

DM_PART_001 = get_requirement_by_id("DM-PART-001")
DM_ART_001 = get_requirement_by_id("DM-ART-001")
DM_MSG_001 = get_requirement_by_id("DM-MSG-001")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _send_and_get_response(
    client: BaseTransportClient,
    prefix: str,
) -> Any:
    """Send a message with the given prefix and return the response.

    Calls ``pytest.skip`` if the message fails.
    """
    message: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK artifact test"}],
        "messageId": tck_id(prefix),
    }
    response = client.send_message(message=message)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@core
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestTextArtifact:
    """DM-ART-001 / DM-PART-001: Task with a text artifact."""

    def test_task_has_text_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Response contains an artifact with a TextPart."""
        req = DM_ART_001
        client = get_client(
            transport_clients, transport,
            compatibility_collector=compatibility_collector, req=req,
        )
        response = _send_and_get_response(client, "artifact-text")

        errors, part = validate_artifact_structure(response, transport, "text")
        if part is not None:
            text = get_part_text(part, transport)
            if text != "Generated text content":
                errors.append(
                    f"Expected text 'Generated text content', got {text!r}"
                )

        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestFileArtifact:
    """DM-ART-001 / DM-PART-001: Task with a file artifact."""

    def test_task_has_file_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Response contains an artifact with a FilePart."""
        req = DM_ART_001
        client = get_client(
            transport_clients, transport,
            compatibility_collector=compatibility_collector, req=req,
        )
        response = _send_and_get_response(client, "artifact-file")

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

        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestFileUrlArtifact:
    """DM-ART-001 / DM-PART-001: Task with a file URL artifact."""

    def test_task_has_file_url_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Response contains an artifact with a FilePart using a URL."""
        req = DM_ART_001
        client = get_client(
            transport_clients, transport,
            compatibility_collector=compatibility_collector, req=req,
        )
        response = _send_and_get_response(client, "artifact-file-url")

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

        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestDataArtifact:
    """DM-ART-001 / DM-PART-001: Task with a data artifact."""

    def test_task_has_data_artifact(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Response contains an artifact with a DataPart."""
        req = DM_ART_001
        client = get_client(
            transport_clients, transport,
            compatibility_collector=compatibility_collector, req=req,
        )
        response = _send_and_get_response(client, "artifact-data")

        errors, part = validate_artifact_structure(response, transport, "data")
        if part is not None:
            data = get_part_data(part, transport)
            expected = {"key": "value", "count": 42}
            if data != expected:
                errors.append(
                    f"Expected data {expected!r}, got {data!r}"
                )

        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestMessageResponse:
    """DM-MSG-001: SendMessage returns a Message (not a Task)."""

    def test_returns_message_with_text_part(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Response is a Message with a TextPart."""
        req = DM_MSG_001
        client = get_client(
            transport_clients, transport,
            compatibility_collector=compatibility_collector, req=req,
        )
        response = _send_and_get_response(client, "message-response")

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

        assert_and_record(compatibility_collector, req, transport, errors)
