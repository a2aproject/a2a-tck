"""Regression tests for the HTTP+JSON transport client (issue #225).

A conformant server may answer a streamed ``message:stream`` request with a
non-2xx status and a JSON error body.  ``_request_streaming`` opens the response
with ``stream=True`` and, on an error status, must make the body readable before
closing it; otherwise ``_extract_error`` (reached via ``.error``) calls
``.json()``/``.text`` on an unread streamed response and raises
``httpx.ResponseNotRead`` (a ``StreamError``/``RuntimeError`` subclass) that the
harness does not expect, crashing HTTP_JSON-SSE-001 instead of skipping.
"""

from __future__ import annotations

import json
import threading

from contextlib import contextmanager, nullcontext
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Iterator

import httpx
import pytest

from tck.reporting.collector import CompatibilityCollector
from tck.transport.http_json_client import HttpJsonClient, _extract_error
from tck.transport.jsonrpc_client import JsonRpcClient
from tck.validators.json_schema import JSONSchemaValidator
from tests.compatibility.core_operations import test_transport_behavior as transport_checks
from tests.compatibility.http_json import test_problem_details as http_json_checks
from tests.compatibility.jsonrpc import test_error_info as jsonrpc_checks


_ERROR_MESSAGE = "task not found"
_ERROR_BODY = json.dumps({"error": {"code": 404, "message": _ERROR_MESSAGE}}).encode()
_STATUS_BAD_REQUEST = 400


class _ErrorHandler(BaseHTTPRequestHandler):
    """Returns 400 with an AIP-193 JSON error body to any streamed POST."""

    status_code = _STATUS_BAD_REQUEST
    response_content_type = "application/a2a+json"

    def response_body(self) -> bytes:
        """Supply the response payload for this real HTTP control server."""
        return _ERROR_BODY

    def do_GET(self) -> None:
        """Use the same response contract for task retrieval."""
        self.do_POST()

    def do_POST(self) -> None:
        # Drain the request body before responding; leaving it unread makes some
        # platforms (notably Windows) reset the connection, which would surface
        # as a spurious httpx.ReadError rather than the 400 under test.
        content_length = int(self.headers.get("Content-Length", 0))
        self._request_body = self.rfile.read(content_length) if content_length else b""
        body = self.response_body()
        self.send_response(self.status_code)
        self.send_header("Content-Type", self.response_content_type)
        self.send_header("X-TCK-Request-Content-Type", self.headers.get("Content-Type", ""))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@contextmanager
def _running_server(handler: type[BaseHTTPRequestHandler]) -> Iterator[str]:
    """Manage a real HTTP server and join its worker before returning."""
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def error_server() -> Iterator[str]:
    """A stdlib HTTP server that answers every POST with a 400 JSON error."""
    with _running_server(_ErrorHandler) as url:
        yield url


def test_streaming_error_does_not_crash_and_returns_message(error_server: str) -> None:
    """Streaming to a server that returns 400 must yield the error string, not raise.

    This is the exact scenario from issue #225: without reading the streamed
    body before close, ``.error`` raised ``httpx.ResponseNotRead``.
    """
    client = HttpJsonClient(error_server)
    try:
        response = client.send_streaming_message(message={"role": "user", "parts": []})
        assert response.success is False
        assert response.status_code == _STATUS_BAD_REQUEST
        # ``.error`` routes through ``_extract_error`` on the closed streamed
        # response; it must return the server's error string, not raise.
        error = response.error
        assert error is not None
        assert "[400]" in error
        assert _ERROR_MESSAGE in error
    finally:
        client.close()


def test_extract_error_on_read_streamed_response(error_server: str) -> None:
    """Suite-level path: ``_extract_error`` on a read+closed streamed response returns a string."""
    with httpx.Client(base_url=error_server) as raw:
        request = raw.build_request("POST", "/message:stream", json={})
        response = raw.send(request, stream=True)
        try:
            assert response.status_code == _STATUS_BAD_REQUEST
            response.read()  # what _request_streaming now does before close()
        finally:
            response.close()
        result = _extract_error(response)
    assert isinstance(result, str)
    assert "[400]" in result
    assert _ERROR_MESSAGE in result


@pytest.mark.parametrize("streaming", [False, True])
def test_requests_use_recommended_media_type(error_server: str, streaming: bool) -> None:
    """Both real HTTP request paths transmit the released binding's media type."""
    client = HttpJsonClient(error_server)
    try:
        send = client.send_streaming_message if streaming else client.send_message
        response = send(message={"role": "ROLE_USER", "parts": [{"text": "media type"}], "messageId": "ct-test"})
        assert response.status_code == _STATUS_BAD_REQUEST
        assert response.headers["x-tck-request-content-type"] == "application/a2a+json"
        assert _ERROR_MESSAGE in response.error
    finally:
        client.close()


@pytest.mark.parametrize("transport", ["jsonrpc", "http_json"])
@pytest.mark.parametrize(
    ("fields", "valid", "recommended"),
    [({}, True, False), ({"value": []}, True, False), ({"value": [{"@type": "example.org/Custom"}]}, True, False),
     ({"value": [{"@type": "type.googleapis.com/google.rpc.BadRequest"}]}, True, True),
     ({"value": None}, False, False), ({"value": {}}, False, False), ({"value": [{}]}, False, False)],
)
def test_compatibility_probes_validate_present_error_details(transport: str, fields: dict, valid: bool, recommended: bool) -> None:
    """The actual probes enforce Any structure on real client responses."""
    error = {"code": -32001 if transport == "jsonrpc" else 404, "message": _ERROR_MESSAGE}
    if "value" in fields:
        error["data" if transport == "jsonrpc" else "details"] = fields["value"]
    body = {"jsonrpc": "2.0", "id": 1, "error": error} if transport == "jsonrpc" else {"error": error}

    class DetailsHandler(_ErrorHandler):
        status_code = 200 if transport == "jsonrpc" else 404
        response_content_type = "application/json" if transport == "jsonrpc" else "application/a2a+json"

        def response_body(self) -> bytes:
            response = {**body, "id": json.loads(self._request_body)["id"]} if transport == "jsonrpc" else body
            return json.dumps(response).encode()

    with _running_server(DetailsHandler) as url:
        client = JsonRpcClient(url) if transport == "jsonrpc" else HttpJsonClient(url)
        collector = CompatibilityCollector()
        try:
            check = (
                jsonrpc_checks.TestJsonRpcErrorDetails().test_present_error_data_is_any_array
                if transport == "jsonrpc"
                else http_json_checks.TestAIP193ErrorFormat().test_present_details_are_typed_objects
            )
            with nullcontext() if valid else pytest.raises(AssertionError):
                check({transport: client}, collector)
            result, = collector.get_results()
            assert result.passed is valid
            assert result.level == "MUST"
            if transport == "jsonrpc":
                collector = CompatibilityCollector()
                with nullcontext() if recommended else pytest.raises(AssertionError):
                    jsonrpc_checks.TestJsonRpcWellKnownErrorDetails().test_error_data_uses_well_known_type({transport: client}, collector)
                result, = collector.get_results()
                assert result.passed is recommended
                assert result.level == "SHOULD"
        finally:
            client.close()


@pytest.mark.parametrize("media_type", ["application/a2a+json", "application/json", "application/a2a+json-invalid"])
def test_compatibility_media_type_probe_records_recommendation(media_type: str) -> None:
    """The response-header probe applies exact matching and records SHOULD."""
    class MediaHandler(_ErrorHandler):
        response_content_type = media_type

    valid = media_type == "application/a2a+json"
    with _running_server(MediaHandler) as url:
        client = HttpJsonClient(url)
        collector = CompatibilityCollector()
        try:
            response = client.send_message(message={"messageId": "ct-probe", "parts": [{"text": "check"}], "role": "ROLE_USER"})
            with nullcontext() if valid else pytest.raises(AssertionError):
                transport_checks.TestRestFormat().test_response_content_type(response, collector)
            result, = collector.get_results()
            assert result.passed is valid
            assert result.level == "SHOULD"
            collector = CompatibilityCollector()
            with nullcontext() if valid else pytest.raises(AssertionError):
                http_json_checks.TestHttpJsonErrorMediaType().test_error_content_type({"http_json": client}, collector)
            result, = collector.get_results()
            assert result.passed is valid
            assert result.level == "SHOULD"
        finally:
            client.close()


@pytest.mark.parametrize("valid", [False, True])
def test_compatibility_schema_probe_remains_mandatory(valid: bool) -> None:
    """The real response-schema probe rejects invalid payloads as a MUST."""
    body = {"message": {"messageId": "reply" if valid else 12, "role": "ROLE_AGENT", "parts": [{"text": "reply"}]}}

    class SchemaHandler(_ErrorHandler):
        status_code = 200

        def response_body(self) -> bytes:
            return json.dumps(body).encode()

    validator = JSONSchemaValidator(Path(__file__).resolve().parents[3] / "specification" / "a2a.json")
    with _running_server(SchemaHandler) as url:
        client = HttpJsonClient(url)
        collector = CompatibilityCollector()
        try:
            response = client.send_message(message={"messageId": "schema-probe", "parts": [{"text": "check"}], "role": "ROLE_USER"})
            with nullcontext() if valid else pytest.raises(AssertionError):
                transport_checks.TestRestFormat().test_response_validates_against_schema(response, {"http_json": validator}, collector)
            result, = collector.get_results()
            assert result.passed is valid
            assert result.level == "MUST"
        finally:
            client.close()


@pytest.mark.parametrize(
    ("test_class", "method", "level"),
    [(transport_checks.TestRestFormat, "test_response_content_type", "should"),
     (transport_checks.TestRestFormat, "test_response_validates_against_schema", "must"),
     (http_json_checks.TestHttpJsonErrorMediaType, "test_error_content_type", "should"),
     (http_json_checks.TestAIP193ErrorFormat, "test_present_details_are_typed_objects", "must"),
     (jsonrpc_checks.TestJsonRpcErrorDetails, "test_present_error_data_is_any_array", "must"),
     (jsonrpc_checks.TestJsonRpcWellKnownErrorDetails, "test_error_data_uses_well_known_type", "should")],
)
def test_probe_level_filters_match_the_recorded_requirements(test_class: type, method: str, level: str) -> None:
    """Selecting MUST or SHOULD runs exactly the matching binding probes."""
    marks = [*getattr(test_class, "pytestmark", []), *getattr(getattr(test_class, method), "pytestmark", [])]
    assert {mark.name for mark in marks} & {"must", "should", "may"} == {level}
