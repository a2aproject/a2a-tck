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
from tck.requirements.base import TASK_NOT_FOUND_ERROR, VERSION_NOT_SUPPORTED_ERROR
from tck.requirements.registry import get_requirement_by_id
from tck.transport.http_json_client import HttpJsonClient, _extract_error
from tck.transport.jsonrpc_client import JsonRpcClient
from tck.validators.error_binding import validate_expected_error
from tck.validators.http_json.error_validator import validate_http_json_error
from tck.validators.json_schema import JSONSchemaValidator
from tests.compatibility.agent_card import test_agent_card_caching as card_cache_checks
from tests.compatibility.core_operations import test_transport_behavior as transport_checks
from tests.compatibility.http_json import test_http_status as http_status_checks
from tests.compatibility.http_json import test_problem_details as http_json_checks
from tests.compatibility.jsonrpc import test_error_info as jsonrpc_checks


_ERROR_MESSAGE = "task not found"
_ERROR_BODY = json.dumps({"error": {"code": 404, "message": _ERROR_MESSAGE}}).encode()
_STATUS_BAD_REQUEST = 400


@contextmanager
def _probe_outcome(expected: bool | None) -> Iterator[None]:
    """Do not let an unexpected probe skip silently skip its regression test."""
    expectation = pytest.raises(pytest.skip.Exception) if expected is None else nullcontext() if expected else pytest.raises(AssertionError)
    try:
        with expectation:
            yield
    except pytest.skip.Exception as error:
        pytest.fail(f"Unexpected compatibility-probe skip: {error}")


class _ErrorHandler(BaseHTTPRequestHandler):
    """Returns 400 with an AIP-193 JSON error body to any streamed POST."""

    status_code = _STATUS_BAD_REQUEST
    response_content_type = "application/a2a+json"
    response_headers: tuple[tuple[str, str], ...] = ()

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
        for name, value in self.response_headers:
            self.send_header(name, value)
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


@pytest.mark.parametrize("code_json,valid", [("404", True), ("404.0", True), ("4.04e2", True), ('"404"', True), ('"4.04e2"', True),
                                          ("404.5", False), ('"404.5"', False), ("true", False), ("2147483648", False), ("[]", False), ("{}", False), ("null", False)])
def test_error_code_accepts_integral_protojson_numbers_on_the_wire(code_json: str, valid: bool) -> None:
    """JSON exponent notation must not turn a conforming int32 into a failure."""
    body = json.dumps({"error": {"code": 0, "message": "not found", "details": [{
        "@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "TASK_NOT_FOUND", "domain": "a2a-protocol.org",
    }]}}).replace('"code": 0', '"code": ' + code_json)

    class NumericCodeHandler(_ErrorHandler):
        status_code = 404

        def response_body(self) -> bytes:
            return body.encode()

    with _running_server(NumericCodeHandler) as url:
        client = HttpJsonClient(url)
        try:
            response = client.get_task(id="numeric-code")
            assert (not validate_expected_error(response, "http_json", TASK_NOT_FOUND_ERROR)) is valid
        finally:
            client.close()


@pytest.mark.parametrize("present", [False, True])
def test_last_modified_is_optional_on_a_real_agent_card_response(present: bool) -> None:
    """An absent MAY header is a recorded skip, never a conformance failure."""
    class CardHandler(_ErrorHandler):
        status_code = 200
        response_headers = (("Last-Modified", "Mon, 19 Oct 2026 12:00:00 GMT"),) if present else ()

        def response_body(self) -> bytes:
            return json.dumps({"name": "Cache control fixture", "description": "Header control", "version": "1",
                               "supportedInterfaces": [{"url": "https://example.test/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
                               "capabilities": {}, "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
                               "skills": [{"id": "echo", "name": "Echo", "description": "Echo", "tags": ["test"]}]}).encode()

    with _running_server(CardHandler) as url:
        collector = CompatibilityCollector()
        with _probe_outcome(True if present else None):
            card_cache_checks.TestAgentCardLastModified().test_last_modified_present(url, collector)
        result, = collector.get_results()
        assert result.passed is present
        assert result.skipped is (not present)
        assert result.level == "MAY"


@pytest.mark.parametrize("message,status,format_valid,semantic_valid", [
    (None, 5, True, True), ("not found", "NOT_FOUND", True, True), (None, None, True, True),
    (7, 5, False, False), (None, 5.5, False, False), (None, "UNKNOWN", True, False),
])
def test_http_error_probes_share_protojson_presence_and_enum_semantics(message: object, status: object, format_valid: bool, semantic_valid: bool) -> None:
    """Exercise all format producers and error-identity validation on real HTTP."""
    class ProtoJSONHandler(_ErrorHandler):
        status_code = 404

        def response_body(self) -> bytes:
            return json.dumps({"error": {"code": 404, "message": message, "status": status, "details": [{
                "@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "TASK_NOT_FOUND", "domain": "a2a-protocol.org",
            }]}}).encode()

    probes = http_json_checks.TestAIP193ErrorFormat()
    with _running_server(ProtoJSONHandler) as url:
        client = HttpJsonClient(url)
        try:
            for probe in (probes.test_error_object_present, probes.test_present_details_are_typed_objects, probes.test_message_field_is_string):
                collector = CompatibilityCollector()
                with _probe_outcome(format_valid):
                    probe({"http_json": client}, collector)
                result, = collector.get_results()
                assert result.passed is format_valid
                assert not result.skipped and result.level == "MUST"
            response = client.get_task(id="protojson-presence")
            assert (not validate_expected_error(response, "http_json", TASK_NOT_FOUND_ERROR)) is semantic_valid
        finally:
            client.close()


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


@pytest.mark.parametrize(
    ("reason", "domain", "valid"),
    [("VERSION_NOT_SUPPORTED", "a2a-protocol.org", True),
     ([], "a2a-protocol.org", False),
     ("UNSUPPORTED_OPERATION", "a2a-protocol.org", False),
     ("VERSION_NOT_SUPPORTED", "other.example", False),
     (None, None, False)],
)
def test_http_error_identity_through_actual_client(reason: object, domain: str | None, valid: bool) -> None:
    """A shared HTTP400 is insufficient, including the real raw-response wrapper."""
    error = {"code": 400, "message": "identity control"}
    if reason is not None:
        error["details"] = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason, "domain": domain}]

    class IdentityHandler(_ErrorHandler):
        def response_body(self) -> bytes:
            return json.dumps({"error": error}).encode()

    with _running_server(IdentityHandler) as url:
        client = HttpJsonClient(url)
        try:
            response = client.get_task(id="identity-control")
            assert not response.success
            assert validate_http_json_error(response.raw_response, "VersionNotSupportedError").valid is valid
            wrapped = {"status_code": response.status_code, "body": response.raw_response}
            assert validate_http_json_error(wrapped, "VersionNotSupportedError").valid is valid
            assert (not validate_expected_error(response, "http_json", VERSION_NOT_SUPPORTED_ERROR)) is valid
            assert validate_expected_error(response, "smtp", VERSION_NOT_SUPPORTED_ERROR) == ["Unknown transport: smtp"]
            collector = CompatibilityCollector()
            with _probe_outcome(valid):
                http_status_checks.TestHttpJsonStatusCodes().test_version_not_supported_returns_400({"http_json": client}, collector)
            result, = collector.get_results()
            assert result.passed is valid and not result.skipped
        finally:
            client.close()


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
    [({}, True, None), ({"value": []}, True, None), ({"value": [{"@type": "example.org/Custom"}]}, True, False),
     ({"value": [{"@type": "type.googleapis.com/google.rpc.BadRequest"}]}, True, True),
     ({"value": None}, False, None), ({"value": {}}, False, None), ({"value": [{}]}, False, None)],
)
def test_compatibility_probes_validate_present_error_details(transport: str, fields: dict, valid: bool, recommended: bool | None) -> None:
    """The actual probes enforce Any structure on real client responses."""
    # HTTP uses ProtoJSON repeated-field presence; JSON-RPC explicitly requires
    # an array when its separate envelope's data member is present.
    if transport == "http_json" and fields == {"value": None}:
        valid = True
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
            with _probe_outcome(valid):
                check({transport: client}, collector)
            result, = collector.get_results()
            assert result.passed is valid
            assert result.level == "MUST"
            if transport == "jsonrpc":
                collector = CompatibilityCollector()
                with _probe_outcome(recommended):
                    jsonrpc_checks.TestJsonRpcWellKnownErrorDetails().test_error_data_uses_well_known_type({transport: client}, collector)
                result, = collector.get_results()
                assert result.passed is (recommended is True)
                assert result.skipped is (recommended is None)
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
            with _probe_outcome(valid):
                transport_checks.TestRestFormat().test_response_content_type(response, collector)
            result, = collector.get_results()
            assert result.passed is valid
            assert result.level == "SHOULD"
            collector = CompatibilityCollector()
            with _probe_outcome(valid):
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
            with _probe_outcome(valid):
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


@pytest.mark.parametrize("card,media_type,skip", [
    ({"defaultInputModes": [], "skills": [{"inputModes": ["application/x-tck-unsupported"]}]}, "application/x-tck-unsupported", True),
    ({"defaultInputModes": ["APPLICATION/X-TCK-UNSUPPORTED; charset=utf-8"]}, "application/x-tck-unsupported", True),
    ({"defaultInputModes": ["application/*; version=1"]}, "application/x-tck-unsupported", True),
    ({"defaultInputModes": ["*/*"]}, "image/x-tck-unsupported", True),
    ({"skills": [{"inputModes": ["IMAGE/*"]}]}, "image/x-tck-unsupported", True),
    ({"defaultInputModes": ["application/*"]}, "image/x-tck-unsupported", False),
    ({"defaultInputModes": ["text/plain"]}, "image/x-tck-unsupported", False),
])
def test_unsupported_media_precondition_respects_all_advertised_modes(card: dict, media_type: str, skip: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    """The actual negative probe sends only a definitely unadvertised part type."""
    requirement = get_requirement_by_id("CORE-SEND-003")
    message = {**requirement.sample_input["message"], "parts": [{**requirement.sample_input["message"]["parts"][0], "mediaType": media_type}]}
    monkeypatch.setattr(requirement, "sample_input", {"message": message})
    received = []

    class UnsupportedMediaHandler(_ErrorHandler):
        def response_body(self) -> bytes:
            received.append(json.loads(self._request_body))
            return json.dumps({"error": {"code": 400, "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "CONTENT_TYPE_NOT_SUPPORTED", "domain": "a2a-protocol.org"}]}}).encode()

    with _running_server(UnsupportedMediaHandler) as url:
        client = HttpJsonClient(url)
        collector = CompatibilityCollector()
        try:
            with _probe_outcome(None if skip else True):
                http_status_checks.TestHttpJsonStatusCodes().test_content_type_not_supported_returns_400({"http_json": client}, card, collector)
            result, = collector.get_results()
            assert result.skipped is skip
            assert result.passed is (not skip)
            assert received == ([] if skip else [{"message": message}])
        finally:
            client.close()


@pytest.mark.parametrize("expected", [True, False])
def test_unexpected_compatibility_skip_is_not_a_green_unit_test(expected: bool) -> None:
    """Exercise the unit harness guard using actual pytest skip/fail signals."""
    with pytest.raises(pytest.fail.Exception, match="Unexpected compatibility-probe skip"), _probe_outcome(expected):
        pytest.skip("unexpected control")


def test_http_missing_task_success_is_a_failure_not_a_skip() -> None:
    """A mandatory missing-resource error is checked even if a faulty server returns200."""
    class SuccessHandler(_ErrorHandler):
        status_code = 200

        def response_body(self) -> bytes:
            return json.dumps({"id": "invented-task"}).encode()

    with _running_server(SuccessHandler) as url:
        client = HttpJsonClient(url)
        collector = CompatibilityCollector()
        try:
            with _probe_outcome(False):
                http_status_checks.TestHttpJsonStatusCodes().test_task_not_found_returns_404({"http_json": client}, collector)
            result, = collector.get_results()
            assert not result.passed and not result.skipped
        finally:
            client.close()


def test_invalid_json_error_body_is_reported_without_crashing() -> None:
    """The actual HTTP response decoder reports malformed untrusted JSON as a failure."""
    class InvalidJsonHandler(_ErrorHandler):
        def response_body(self) -> bytes:
            return b"{"

    with _running_server(InvalidJsonHandler) as url:
        client = HttpJsonClient(url)
        try:
            response = client.get_task(id="invalid-json-control")
            result = validate_http_json_error(response.raw_response, "VersionNotSupportedError")
            assert not result.valid
            assert "Invalid AIP-193" in result.message
        finally:
            client.close()
