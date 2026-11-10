"""Tests for operator-supplied A2A message parts."""

from __future__ import annotations

import json

from typing import TYPE_CHECKING

import pytest

from tck.message_parts import MessagePartsError, load_message_parts


if TYPE_CHECKING:
    from pathlib import Path


def test_load_message_parts_reads_non_empty_object_array(tmp_path: Path) -> None:
    """A fixture file is the exact A2A Message.parts array to send."""
    path = tmp_path / "parts.json"
    expected = [{"data": {"decision": "approve"}, "mediaType": "application/json"}]
    path.write_text(json.dumps(expected), encoding="utf-8")

    assert load_message_parts(path) == expected


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        ["not-an-object"],
    ],
)
def test_load_message_parts_rejects_invalid_shapes(tmp_path: Path, payload: object) -> None:
    """Invalid fixture shapes fail before any SUT request is made."""
    path = tmp_path / "parts.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MessagePartsError):
        load_message_parts(path)


def test_load_message_parts_rejects_invalid_json(tmp_path: Path) -> None:
    """Malformed JSON produces a configuration error."""
    path = tmp_path / "parts.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(MessagePartsError):
        load_message_parts(path)
