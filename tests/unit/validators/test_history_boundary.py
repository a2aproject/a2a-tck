"""Native fixture replay and reselected failure controls for the opt-in profile."""

from __future__ import annotations

import copy
import hashlib
import json
import logging

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from hypothesis import given
from hypothesis import strategies as st

from tck.requirements.base import RequirementLevel
from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import JsonRpcResponse
from tck.validators.history_boundary import validate_history_boundary
from tck.validators.history_boundary_corpus import (
    CASE_IDS,
    SELECTED_MANIFEST_SHA256,
    history_boundary_arguments,
    load_history_boundary_corpus,
    replay_history_boundary_corpus,
)


if TYPE_CHECKING:
    from pytest import LogCaptureFixture


CORPUS_DIRECTORY = Path(__file__).resolve().parents[3] / "conformance-vectors" / "a2a-history-boundary-v01"
RECORDS = load_history_boundary_corpus(CORPUS_DIRECTORY, manifest_sha256=SELECTED_MANIFEST_SHA256)
ACCEPTED = RECORDS[0]
REJECTED = RECORDS[1]
REFUSAL_PREFIX = "History boundary refused: "


def _set(record: dict[str, Any], path: tuple[str | int, ...], value: Any) -> None:
    """Alter a selected nested boundary while preserving all unrelated evidence."""
    parent: Any = record
    for name in path[:-1]:
        parent = parent[name]
    parent[path[-1]] = value


def _validate(record: dict[str, Any]) -> list[str]:
    """Execute the actual TCK adapter and validator without a fake SUT."""
    return validate_history_boundary(**history_boundary_arguments(record))


def _reselect(directory: Path, corpus: dict[str, Any], manifest: dict[str, Any]) -> str:
    """Reselect tampered bytes to test semantics beyond raw digest refusal."""
    raw = (json.dumps(corpus, indent=2) + "\n").encode()
    (directory / "corpus.json").write_bytes(raw)
    manifest["corpusSha256"] = hashlib.sha256(raw).hexdigest()
    raw_manifest = (json.dumps(manifest, indent=2) + "\n").encode()
    (directory / "manifest.json").write_bytes(raw_manifest)
    return hashlib.sha256(raw_manifest).hexdigest()


class TestHistoryBoundary:
    """Public-host API behavior over authentic controlled caller/readback cases."""

    class TestPassingCases:
        """Retain native accepted/persisted and rejected/absent populations."""

        @pytest.mark.parametrize("record", RECORDS, ids=CASE_IDS)
        def test_native_case(self, record: dict[str, Any], caplog: LogCaptureFixture) -> None:
            """Each original native case passes without emitting a refusal log."""
            assert _validate(record) == []
            assert REFUSAL_PREFIX not in caplog.text

        def test_complete_population_and_scope(self) -> None:
            """Replay every fixed identity without adding a normative severity."""
            report = replay_history_boundary_corpus(CORPUS_DIRECTORY, manifest_sha256=SELECTED_MANIFEST_SHA256)
            assert report["passed"] is True
            assert report["status"] == "provisional-application-profile"
            assert tuple(row["id"] for row in report["records"]) == CASE_IDS
            assert get_requirement_by_id("CORE-HIST-004").level is RequirementLevel.MAY

        @given(request_id=st.one_of(st.integers(), st.text(min_size=1)))
        def test_literal_request_identifiers(self, request_id: str | int) -> None:
            """Matching string/integer identifiers preserve the observed boundary."""
            record = copy.deepcopy(ACCEPTED)
            record["request"]["id"] = request_id
            record["sendResponse"]["id"] = request_id
            assert _validate(record) == []

    class TestFailingCases:
        """False caller, history, identity and error boundaries fail precisely."""

        @pytest.mark.parametrize(
            ("case", "path", "value", "reason"),
            [
                (ACCEPTED, ("outcome",), "arbitrary-error", "Unknown selected history boundary outcome"),
                (ACCEPTED, ("request", "id"), "other", "Caller response does not match JSON-RPC request"),
                (ACCEPTED, ("request", "id"), True, "Request id must be a nonempty string or integer"),
                (ACCEPTED, ("httpStatus",), 201, "Selected caller requires HTTP status 200"),
                (ACCEPTED, ("httpStatus",), True, "Selected caller requires HTTP status 200"),
                (ACCEPTED, ("sendResponse", "jsonrpc"), "1.0", "Caller response does not match JSON-RPC request"),
                (ACCEPTED, ("sendResponse", "extra"), None, "Caller response fields differ from selected outcome"),
                (ACCEPTED, ("beforeTask", "history"), None, "Selected persisted Task requires complete history"),
                (ACCEPTED, ("persistedTask", "history"), None, "Selected persisted Task requires complete history"),
                (ACCEPTED, ("beforeTask", "id"), "", "Task requires a nonempty id"),
                (ACCEPTED, ("persistedTask", "contextId"), "", "Task requires a nonempty contextId"),
                (ACCEPTED, ("request", "params", "message", "role"), "ROLE_AGENT", "Selected follow-up must be a user message"),
                (ACCEPTED, ("request", "params", "message", "messageId"), "", "Follow-up requires a nonempty messageId"),
                (ACCEPTED, ("request", "params", "message", "parts"), [], "Follow-up requires message parts"),
                (ACCEPTED, ("request", "params", "message", "taskId"), "other", "Follow-up and readback task identity differ"),
                (ACCEPTED, ("persistedTask", "id"), "other", "Follow-up and readback task identity differ"),
                (
                    ACCEPTED,
                    ("request", "params", "message", "contextId"),
                    "other",
                    "Follow-up and readback context identity differ",
                ),
                (ACCEPTED, ("beforeTask", "history"), [None], "History messages must be objects"),
                (ACCEPTED, ("beforeTask", "status", "state"), "TASK_STATE_COMPLETED", "Selected prior Task must require input"),
                (ACCEPTED, ("beforeTask", "status", "message"), None, "Selected prior Task requires its pending agent message"),
                (
                    ACCEPTED,
                    ("beforeTask", "history", 0, "messageId"),
                    ACCEPTED["request"]["params"]["message"]["messageId"],
                    "Follow-up messageId must be distinct from prior history",
                ),
                (
                    ACCEPTED,
                    ("persistedTask", "history"),
                    ACCEPTED["beforeTask"]["history"],
                    "Accepted follow-up must persist exactly once after prior history",
                ),
                (
                    ACCEPTED,
                    ("sendResponse", "result", "task", "history"),
                    ACCEPTED["beforeTask"]["history"],
                    "Accepted caller Task must match persisted readback",
                ),
                (REJECTED, ("sendResponse", "error", "code"), -32001, "Rejected follow-up must expose InternalError (-32603)"),
                (REJECTED, ("sendResponse", "error", "code"), False, "Rejected follow-up must expose InternalError (-32603)"),
                (
                    REJECTED,
                    ("sendResponse", "error", "message"),
                    "Internal error",
                    "Rejected caller must preserve the native concurrent-modification error",
                ),
                (REJECTED, ("sendResponse", "error", "data"), [], "Rejected caller must preserve native InternalError details"),
                (REJECTED, ("sendResponse", "error"), [], "Rejected caller must contain an error object"),
                (
                    REJECTED,
                    ("persistedTask", "status", "state"),
                    "TASK_STATE_FAILED",
                    "Rejected follow-up must be absent from unchanged persisted Task",
                ),
                (
                    REJECTED,
                    ("persistedTask", "history"),
                    [*REJECTED["beforeTask"]["history"], REJECTED["request"]["params"]["message"]],
                    "Rejected follow-up must be absent from unchanged persisted Task",
                ),
            ],
        )
        def test_boundary_mutation(
            self, case: dict[str, Any], path: tuple[str | int, ...], value: Any, reason: str, caplog: LogCaptureFixture
        ) -> None:
            """Each independently changed semantic boundary refuses with its reason."""
            record = copy.deepcopy(case)
            _set(record, path, copy.deepcopy(value))
            with caplog.at_level(logging.WARNING, logger="tck.validators.history_boundary"):
                assert _validate(record) == [reason]
            assert REFUSAL_PREFIX + reason in caplog.text

        @pytest.mark.parametrize("transport", ["grpc", "http_json", "unknown"])
        def test_unsupported_transport(self, transport: str, caplog: LogCaptureFixture) -> None:
            """The selected JSON-RPC profile cannot silently cover another binding."""
            args = history_boundary_arguments(copy.deepcopy(ACCEPTED))
            args["send_response"].transport = transport
            reason = "History boundary profile requires JSON-RPC"
            assert validate_history_boundary(**args) == [reason]
            assert REFUSAL_PREFIX + reason in caplog.text

        @pytest.mark.parametrize("flag", [True, 0, "false"])
        def test_rejected_success_flag(self, flag: Any, caplog: LogCaptureFixture) -> None:
            """Explicit caller failure cannot be replaced by truthy/false-like values."""
            args = history_boundary_arguments(copy.deepcopy(REJECTED))
            args["send_response"].success = flag
            reason = (
                "Rejected follow-up must expose a failed caller response"
                if flag is True
                else "Response success must be a boolean"
            )
            assert validate_history_boundary(**args) == [reason]
            assert REFUSAL_PREFIX + reason in caplog.text

        @given(replacement=st.text().filter(lambda value: value != "public fixture turn"))
        def test_correlated_reply_readback_tampering(self, replacement: str) -> None:
            """Matching forged reply/readback cannot erase the original submitted part."""
            record = copy.deepcopy(ACCEPTED)
            record["persistedTask"]["history"][-1]["parts"][0]["text"] = replacement
            record["sendResponse"]["result"]["task"] = copy.deepcopy(record["persistedTask"])
            assert _validate(record) == ["Accepted follow-up must persist exactly once after prior history"]

        @pytest.mark.parametrize("case", [ACCEPTED, REJECTED])
        def test_correlated_pending_agent_identity(self, case: dict[str, Any], caplog: LogCaptureFixture) -> None:
            """Correlated readback cannot reuse the pending agent's message identity."""
            record = copy.deepcopy(case)
            record["beforeTask"]["status"]["message"]["messageId"] = record["request"]["params"]["message"]["messageId"]
            if record["outcome"] == "accepted-and-persisted":
                record["persistedTask"]["history"][-2] = copy.deepcopy(record["beforeTask"]["status"]["message"])
                record["sendResponse"]["result"]["task"] = copy.deepcopy(record["persistedTask"])
            else:
                record["persistedTask"] = copy.deepcopy(record["beforeTask"])
            reason = "Follow-up messageId must be distinct from pending agent message"
            assert _validate(record) == [reason]
            assert REFUSAL_PREFIX + reason in caplog.text

        def test_lost_readback(self, caplog: LogCaptureFixture) -> None:
            """Caller success cannot compensate for a failed persisted reader."""
            args = history_boundary_arguments(copy.deepcopy(ACCEPTED))
            args["readback_response"] = JsonRpcResponse(
                transport="jsonrpc", success=False, raw_response={"error": {"code": -32603}}
            )
            reason = "Persisted Task readback must succeed"
            assert validate_history_boundary(**args) == [reason]
            assert REFUSAL_PREFIX + reason in caplog.text


class TestHistoryBoundaryCorpus:
    """External byte selection and complete source-linked population checks."""

    class TestPassingCases:
        """A source-pinned portable corpus has all twenty original identities."""

        def test_selected_original(self) -> None:
            """The externally fixed manifest and all projected bytes read unchanged."""
            assert tuple(row["id"] for row in RECORDS) == CASE_IDS
            assert all(len(row["sourceCaseSha256"]) == hashlib.sha256().digest_size * 2 for row in RECORDS)

    class TestFailingCases:
        """Digest and reselected-semantic corruption cannot report a complete run."""

        def test_unselected_manifest(self) -> None:
            """An arbitrary replacement pin is refused before any fixture verdict."""
            with pytest.raises(ValueError, match=r"^Selected manifest digest differs$"):
                load_history_boundary_corpus(CORPUS_DIRECTORY, manifest_sha256="0" * 64)

        @pytest.mark.parametrize(
            ("path", "value", "reason"),
            [
                (("status",), "normative-conformance", "History corpus profile or scope differs"),
                (("transport",), "grpc", "History corpus profile or scope differs"),
                (("records",), RECORDS[:-1], "History corpus population differs"),
                (("records", 0, "id"), "other", "History corpus population differs"),
                (("records", 0, "sourceCaseSha256"), "0" * 64, "History corpus source-case bindings differ"),
            ],
        )
        def test_reselected_semantic_mutation(self, tmp_path: Path, path: tuple[str | int, ...], value: Any, reason: str) -> None:
            """Rehashed changed input still fails complete-population/scope semantics."""
            corpus = json.loads((CORPUS_DIRECTORY / "corpus.json").read_bytes())
            manifest = json.loads((CORPUS_DIRECTORY / "manifest.json").read_bytes())
            _set(corpus, path, copy.deepcopy(value))
            pin = _reselect(tmp_path, corpus, manifest)
            with pytest.raises(ValueError, match="^" + reason + "$"):
                load_history_boundary_corpus(tmp_path, manifest_sha256=pin)
