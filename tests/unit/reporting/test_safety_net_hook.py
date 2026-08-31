"""Tests for the safety-net hook helpers in compatibility/conftest.py."""

from __future__ import annotations

import sys

from types import SimpleNamespace, TracebackType
from unittest.mock import MagicMock

import pytest

# The helper lives in a conftest, so import it via its module path.
from tests.compatibility.conftest import (
    _extract_from_crashed_frame,
    _extract_requirement_and_transport,
)


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


def _crash_with_locals(req: object, transport: object) -> None:
    """Assign req/transport as real locals, then raise.

    Mirrors the shape of a compatibility test that crashes before its own
    record() call.
    """
    raise ValueError("simulated crash before record()")


def _get_traceback(**kwargs: object) -> TracebackType:
    """Run _crash_with_locals and return the traceback of the raised exception."""
    try:
        _crash_with_locals(**kwargs)
    except ValueError:
        return sys.exc_info()[2]
    raise AssertionError("expected _crash_with_locals to raise")


class TestExtractFromCrashedFrame:
    """_extract_from_crashed_frame recovers metadata the docstring path misses."""

    def test_recovers_req_id_and_transport_from_locals(self) -> None:
        """A req local with an .id attribute and a string transport local are both found."""
        req = SimpleNamespace(id="CORE-CAP-002")
        tb = _get_traceback(req=req, transport="jsonrpc")
        item = SimpleNamespace(function=_crash_with_locals)
        call = SimpleNamespace(excinfo=SimpleNamespace(tb=tb))

        req_id, transport = _extract_from_crashed_frame(item, call)
        assert req_id == "CORE-CAP-002"
        assert transport == "jsonrpc"

    def test_no_req_local_returns_none_id(self) -> None:
        """Missing req local yields a None requirement ID, not a crash."""
        tb = _get_traceback(req=None, transport="jsonrpc")
        item = SimpleNamespace(function=_crash_with_locals)
        call = SimpleNamespace(excinfo=SimpleNamespace(tb=tb))

        req_id, transport = _extract_from_crashed_frame(item, call)
        assert req_id is None
        assert transport == "jsonrpc"

    def test_non_string_transport_local_returns_none(self) -> None:
        """A transport local that isn't a string (e.g. left at its default None) is ignored."""
        req = SimpleNamespace(id="CORE-CAP-002")
        tb = _get_traceback(req=req, transport=None)
        item = SimpleNamespace(function=_crash_with_locals)
        call = SimpleNamespace(excinfo=SimpleNamespace(tb=tb))

        req_id, transport = _extract_from_crashed_frame(item, call)
        assert req_id == "CORE-CAP-002"
        assert transport is None

    def test_no_excinfo_returns_none_none(self) -> None:
        """A call with no exception info (shouldn't normally happen) is a no-op."""
        item = SimpleNamespace(function=_crash_with_locals)
        call = SimpleNamespace(excinfo=None)

        req_id, transport = _extract_from_crashed_frame(item, call)
        assert req_id is None
        assert transport is None

    def test_no_function_returns_none_none(self) -> None:
        """An item with no function attribute is a no-op."""
        tb = _get_traceback(req=SimpleNamespace(id="X-Y-001"), transport="grpc")
        item = SimpleNamespace(function=None)
        call = SimpleNamespace(excinfo=SimpleNamespace(tb=tb))

        req_id, transport = _extract_from_crashed_frame(item, call)
        assert req_id is None
        assert transport is None
