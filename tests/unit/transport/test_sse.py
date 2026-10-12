"""SSE framing regressions exercised through both HTTP transport clients."""

from __future__ import annotations

import json

from typing import TYPE_CHECKING

import httpx
import pytest

from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from tck.transport.base import StreamingResponse


@pytest.fixture(params=[HttpJsonClient, JsonRpcClient], ids=["http_json", "jsonrpc"])
def open_stream(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable]:
    """Inject MockTransport through the client's public constructor."""
    real_client = httpx.Client
    clients = []

    def open_response(stream: httpx.SyncByteStream, operation: str) -> StreamingResponse:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["accept"] == "text/event-stream"
            return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handler)))
        client: HttpJsonClient | JsonRpcClient = request.param("http://sut.test")
        clients.append(client)
        if operation == "send_streaming_message":
            return client.send_streaming_message(message={"role": "user", "parts": []})
        return client.subscribe_to_task(id="task-1")

    yield open_response
    for client in clients:
        client.close()


@pytest.mark.parametrize("operation", ["send_streaming_message", "subscribe_to_task"])
@pytest.mark.parametrize("line_ending", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
def test_multiline_sse(open_stream: Callable, operation: str, line_ending: str) -> None:
    """Join all data lines before decoding, regardless of wire line endings."""
    body = line_ending.join(['data: {"task":', 'data: {"id": "task-1"}}', "", ""]).encode()
    response = open_stream(httpx.ByteStream(body), operation)
    assert response.success
    assert list(response.events) == [{"task": {"id": "task-1"}}]


@pytest.mark.parametrize("operation", ["send_streaming_message", "subscribe_to_task"])
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param('data: {"id": "task:1"}\n\n', [{"id": "task:1"}], id="single-line"),
        pytest.param('data:{"id": 1}\n\n', [{"id": 1}], id="no-value-space"),
        pytest.param(
            ": heartbeat\n\nevent: update\nid: 1\nretry: 1000\nunknown: ignored\nData: ignored\n"
            'data: {"id":\n: heartbeat\nevent: update\ndata: 1}\n\n',
            [{"id": 1}],
            id="comments-control-and-unknown-fields",
        ),
        pytest.param('data: {"id": 1}\n\n\n: ping\n\ndata: {"id": 2}\n\n', [{"id": 1}, {"id": 2}], id="reset"),
        pytest.param('data: {"id":\n \n\t\ndata: 1}\n\n', [{"id": 1}], id="whitespace-not-boundary"),
        pytest.param(' data: {"id": 1}\n\tdata: {"id": 2}\ndata : {"id": 3}\n\n', [], id="literal-field-names"),
        pytest.param('\ufeffdata: {"id": 1}\n\n', [{"id": 1}], id="leading-bom"),
        pytest.param('\ufeff\ufeffdata: {"id": 1}\n\n', [], id="only-one-leading-bom"),
        pytest.param(': ping\n\n\ufeffdata: {"id": 1}\n\n', [], id="nonleading-bom"),
        pytest.param('data: {"id": 1}', [], id="eof-without-newline"),
        pytest.param('data: {"id": 1}\n', [], id="eof-without-blank-line"),
        pytest.param('data: {"id": 1}\n\n data: ignored\ndata: {"id":', [{"id": 1}], id="incomplete-tail"),
        pytest.param('data: {"id": 1}\n \n', [], id="whitespace-terminated-tail"),
        pytest.param('data: {\ndata\ndata:\ndata: "id": 1}\n\n', [{"id": 1}], id="empty-data-lines"),
    ],
)
def test_sse_framing(open_stream: Callable, operation: str, body: str, expected: list[dict]) -> None:
    """Respect event boundaries and literal SSE field syntax."""
    response = open_stream(httpx.ByteStream(body.encode()), operation)
    assert response.success
    assert list(response.events) == expected


@pytest.mark.parametrize("operation", ["send_streaming_message", "subscribe_to_task"])
@pytest.mark.parametrize(
    ("body", "payload"),
    [
        pytest.param('data: {"id":}\n\n', '{"id":}', id="malformed-json"),
        pytest.param('data: {"id": 1}\ndata: {"id": 2}\n\n', '{"id": 1}\n{"id": 2}', id="two-values-one-event"),
        pytest.param('data: {"id": 1}\n \ndata: {"id": 2}\n\n', '{"id": 1}\n{"id": 2}', id="space-not-boundary"),
        pytest.param("data:  invalid  \n\n", " invalid  ", id="remove-only-one-space"),
        pytest.param('data:\u00a0{"id": 1}\n\n', '\u00a0{"id": 1}', id="non-ascii-value-space"),
        pytest.param("data\n\n", "", id="colonless-empty-data"),
        pytest.param("data:\n\n", "", id="empty-data"),
    ],
)
def test_completed_invalid_sse_json(open_stream: Callable, operation: str, body: str, payload: str) -> None:
    """Expose malformed completed payloads without normalizing their contents."""
    response = open_stream(httpx.ByteStream(body.encode()), operation)
    with pytest.raises(json.JSONDecodeError) as error:
        list(response.events)
    assert error.value.doc == payload


@pytest.mark.parametrize("operation", ["send_streaming_message", "subscribe_to_task"])
def test_sse_yields_at_boundary_before_eof(open_stream: Callable, operation: str) -> None:
    """Read through the boundary, but yield without consuming the next event."""
    consumed = []

    class ChunkedStream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            consumed.append("data")
            yield b'data: {"id": 1}\n'
            consumed.append("boundary")
            yield b"\n"
            consumed.append("second-event")
            yield b'data: {"id": 2}\n\n'
            consumed.append("eof")

    response = open_stream(ChunkedStream(), operation)
    assert consumed == []
    assert next(response.events) == {"id": 1}
    assert consumed == ["data", "boundary"]
    assert next(response.events) == {"id": 2}
    assert consumed == ["data", "boundary", "second-event"]
    assert list(response.events) == []
    assert consumed[-1] == "eof"
