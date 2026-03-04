"""Tests for the safety-net hook helpers in compatibility/conftest.py."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# The helper lives in a conftest, so import it via its module path.
from tests.compatibility.conftest import _extract_requirement_and_transport


def _make_item(
    *,
    docstring: str | None = None,
    transport_param: str | None = None,
    transport_marker: str | None = None,
) -> MagicMock:
    """Build a minimal mock ``pytest.Item``."""
    item = MagicMock(spec=pytest.Item)

    # Function with docstring
    func = MagicMock()
    func.__doc__ = docstring
    item.function = func

    # Parametrized transport via callspec
    if transport_param is not None:
        item.callspec = SimpleNamespace(params={"transport": transport_param})
    else:
        del item.callspec  # no callspec attribute

    # Marker-based transport
    def _get_closest_marker(name: str) -> object | None:
        if name == transport_marker:
            return True
        return None

    item.get_closest_marker = _get_closest_marker
    return item


class TestExtractRequirementAndTransport:
    """_extract_requirement_and_transport parses items correctly."""

    def test_parametrized_transport_and_docstring(self) -> None:
        """Parametrized transport and docstring requirement ID are extracted."""
        item = _make_item(
            docstring="CORE-GET-001: Verify agent card retrieval.",
            transport_param="jsonrpc",
        )
        req_id, transport = _extract_requirement_and_transport(item)
        assert req_id == "CORE-GET-001"
        assert transport == "jsonrpc"

    def test_marker_transport(self) -> None:
        """Transport is extracted from a pytest marker."""
        item = _make_item(
            docstring="CORE-ERR-002: Error handling test.",
            transport_marker="grpc",
        )
        req_id, transport = _extract_requirement_and_transport(item)
        assert req_id == "CORE-ERR-002"
        assert transport == "grpc"

    def test_no_docstring_returns_none(self) -> None:
        """Missing docstring causes (None, None) return."""
        item = _make_item(
            docstring=None,
            transport_param="jsonrpc",
        )
        req_id, transport = _extract_requirement_and_transport(item)
        assert req_id is None
        assert transport is None

    def test_no_transport_returns_none(self) -> None:
        """Missing transport causes (None, None) return."""
        item = _make_item(
            docstring="CORE-GET-001: Something.",
        )
        req_id, transport = _extract_requirement_and_transport(item)
        assert req_id is None
        assert transport is None

    def test_no_requirement_id_in_docstring(self) -> None:
        """Docstring without a requirement ID causes (None, None) return."""
        item = _make_item(
            docstring="This test has no requirement ID.",
            transport_param="grpc",
        )
        req_id, transport = _extract_requirement_and_transport(item)
        assert req_id is None
        assert transport is None

    def test_parametrized_takes_precedence_over_marker(self) -> None:
        """Parametrized transport takes precedence over marker."""
        item = _make_item(
            docstring="CORE-GET-001: Test.",
            transport_param="http_json",
            transport_marker="grpc",
        )
        req_id, transport = _extract_requirement_and_transport(item)
        assert req_id == "CORE-GET-001"
        assert transport == "http_json"
