"""Pinned portable fixtures for the provisional caller/history profile."""

from __future__ import annotations

import hashlib
import json

from typing import TYPE_CHECKING, Any, cast

from tck.transport.jsonrpc_client import JsonRpcResponse
from tck.validators.history_boundary import validate_history_boundary


if TYPE_CHECKING:
    from pathlib import Path


PROFILE = "a2a-history-boundary-v01"
STATUS = "provisional-application-profile"
SELECTED_MANIFEST_SHA256 = "cd7dd03423b9326bdf0c784b0bbefa5e07f4cb17f33c64e688d3b43f2c8393d6"
CASE_IDS = tuple(f"{kind}-{index:02d}" for index in range(10) for kind in ("accepted-retry", "rejected-absent"))


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicated JSON names before interpreting a fixture."""
    value: dict[str, Any] = {}
    for name, child in pairs:
        if name in value:
            raise ValueError("Duplicate JSON name in history corpus")
        value[name] = child
    return value


def _nonfinite(value: str) -> None:
    """Reject nonfinite constants outside the selected JSON contract."""
    raise ValueError(f"Nonfinite JSON constant in history corpus: {value}")


def _decode(raw: bytes) -> Any:
    """Read finite JSON with unambiguous object names."""
    return json.loads(raw, object_pairs_hook=_object, parse_constant=_nonfinite)


def _digest(raw: bytes, expected: str, label: str) -> None:
    """Bind selected raw bytes before parsing their contents."""
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Selected {label} digest differs")


def load_history_boundary_corpus(directory: Path, *, manifest_sha256: str) -> list[dict[str, Any]]:
    """Load the complete twenty-case profile under an external manifest pin.

    The caller selects ``manifest_sha256`` outside the corpus. The fixed
    manifest binds source-case digests, scope, source revision and projected
    caller/readback bytes. This function does not authenticate a new live run.
    ``replay_history_boundary.py`` additionally reproduces every projection
    against the installed native reader and original source packet.
    """
    manifest_raw = (directory / "manifest.json").read_bytes()
    _digest(manifest_raw, manifest_sha256, "manifest")
    manifest = _decode(manifest_raw)
    raw = (directory / "corpus.json").read_bytes()
    _digest(raw, manifest["corpusSha256"], "corpus")
    corpus = _decode(raw)
    _population(corpus, manifest)
    return cast("list[dict[str, Any]]", corpus["records"])


def _population(corpus: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Require exact literal identities and original per-case source digests."""
    if (corpus["profile"], corpus["status"], corpus["transport"]) != (PROFILE, STATUS, "jsonrpc"):
        raise ValueError("History corpus profile or scope differs")
    if tuple(row["id"] for row in corpus["records"]) != CASE_IDS:
        raise ValueError("History corpus population differs")
    actual = [{"id": row["id"], "sourceCaseSha256": row["sourceCaseSha256"]} for row in corpus["records"]]
    if actual != manifest["records"]:
        raise ValueError("History corpus source-case bindings differ")


def history_boundary_arguments(record: dict[str, Any]) -> dict[str, Any]:
    """Adapt retained native Task readback through public TCK response APIs.

    Only ``send_response`` is an original wire response. The before/readback
    responses wrap original native Tasks for public TCK extraction and are
    explicitly not new GetTask network observations. The projected request
    preserves the actual native caller's message and RPC identifier.
    """
    body = record["sendResponse"]
    send = JsonRpcResponse(transport="jsonrpc", success="error" not in body, raw_response=body, status_code=record["httpStatus"])
    return {
        "send_response": send,
        "before_response": JsonRpcResponse(transport="jsonrpc", success=True, raw_response={"result": record["beforeTask"]}),
        "readback_response": JsonRpcResponse(transport="jsonrpc", success=True, raw_response={"result": record["persistedTask"]}),
        "message": record["request"]["params"]["message"],
        "request_id": record["request"]["id"],
        "outcome": record["outcome"],
    }


def project_native_history_case(raw: bytes, *, case_id: str) -> dict[str, Any]:
    """Project original raw SDK/SQL receipts into one portable TCK fixture.

    The native installed reader must first authenticate and validate the
    complete source packet. This deterministic projection preserves exact
    wire request/reply objects, the before/committed native Tasks and a digest
    of all original case bytes, including protobuf, SQL and CAS traces.
    """
    case = _decode(raw)
    if case["id"] != case_id:
        raise ValueError("Native source case identity differs")
    outcomes = {1: "accepted-and-persisted", 2: "rejected-and-absent-with-InternalError"}
    return {
        "id": case_id,
        "sourceCaseSha256": hashlib.sha256(raw).hexdigest(),
        "outcome": outcomes[case["conflictBudget"]],
        "beforeTask": case["before"]["task"],
        "request": _decode(bytes.fromhex(case["followup"]["requestHex"])),
        "sendResponse": _decode(bytes.fromhex(case["followup"]["responseHex"])),
        "httpStatus": case["followup"]["status"],
        "persistedTask": case["final"]["task"],
    }


def replay_history_boundary_corpus(directory: Path, *, manifest_sha256: str) -> dict[str, Any]:
    """Run the public validator over every pinned record without a live SUT."""
    records = load_history_boundary_corpus(directory, manifest_sha256=manifest_sha256)
    results = [
        {"id": row["id"], "outcome": row["outcome"], "errors": validate_history_boundary(**history_boundary_arguments(row))}
        for row in records
    ]
    return {"profile": PROFILE, "status": STATUS, "records": results, "passed": all(not row["errors"] for row in results)}
