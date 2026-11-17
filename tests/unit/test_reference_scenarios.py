"""Keep optional reference outputs separate from protocol conformance."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from google.protobuf.json_format import ParseDict

from specification.generated import a2a_pb2
from tck.reporting.aggregator import CompatibilityAggregator
from tck.reporting.collector import CompatibilityCollector
from tck.validators.json_schema import JSONSchemaValidator
from tck.validators.jsonrpc.response_validator import JsonRpcResponseValidator
from tck.validators.observed_response import observed_checks
from tck.validators.proto_schema import ProtoSchemaValidator
from tests.compatibility.core_operations import test_artifacts as cases
from tests.compatibility.core_operations import test_data_model as data_model


if TYPE_CHECKING:
    from collections.abc import Callable


ROOT = Path(__file__).resolve().parents[2]
MODULE = "tests/compatibility/core_operations/test_artifacts.py"
TRANSPORTS = ("jsonrpc", "http_json", "grpc")


def test_undeclared_and_unsupported_are_not_passes(tmp_path: Path) -> None:
    """A deliberately unreachable URL is never contacted for unselected fixtures."""
    report = tmp_path / "cases.xml"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", MODULE, "--reference-scenario=artifact-file=unsupported",
         "--sut-host=http://127.0.0.1:1", f"--junitxml={report}", "-q"],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    items = ET.parse(report).findall(".//testcase")
    reasons = [item.find("skipped").attrib["message"] for item in items]
    fixture_count = 5
    assert len(items) == fixture_count * len(TRANSPORTS)
    assert sum("UNSUPPORTED" in reason for reason in reasons) == len(TRANSPORTS)
    assert sum("NOT_APPLICABLE" in reason for reason in reasons) == (fixture_count - 1) * len(TRANSPORTS)


@pytest.mark.parametrize("options", [
    ["unused=run"], ["artifact-text=maybe"], ["artifact-text"],
    ["artifact-text=run", "artifact-text=unsupported"],
])
def test_bad_declaration_is_a_configuration_error(options: list[str]) -> None:
    """Invalid declarations must not silently disable cases."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", MODULE, "--collect-only", "-q",
         *(f"--reference-scenario={option}" for option in options)],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
    )
    assert result.returncode == pytest.ExitCode.USAGE_ERROR, result.stdout + result.stderr


def test_run_cannot_silently_be_filtered_out() -> None:
    """Reject an explicit run declaration combined with an excluding MUST filter."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", MODULE, "-m", "must", "--reference-scenario=artifact-text=run",
         "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
    )
    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert "NOT_RUN" in result.stderr


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_unobserved_fields_receive_no_credit(transport: str) -> None:
    """A task with no history, status message or artifacts cannot witness those objects."""
    payload = {"task": {"id": "t", "status": {"state": "TASK_STATE_INPUT_REQUIRED"},
                        "metadata": {"message": {}, "parts": [], "artifacts": [{}]}}}
    raw = ParseDict(payload, a2a_pb2.SendMessageResponse()) if transport == "grpc" else payload
    checks = observed_checks({"result": raw} if transport == "jsonrpc" else raw, transport)
    assert not {"DM-ART-001", "DM-PART-001", "DM-MSG-001"}.intersection(checks)
    assert "DM-TASK-001" in checks and not any(checks.values())


@pytest.mark.parametrize("unavailable", [True, False], ids=["skipped-in-setup", "failed-in-call"])
def test_selected_contract_is_never_counted_as_protocol_evidence(tmp_path: Path, unavailable: bool) -> None:
    """A selected reference contract's skip or failure stays in JUnit, even with an ID in its docstring."""
    probe = tmp_path / "test_probe.py"
    probe.write_text(
        "import pytest\n"
        "def test_control(compatibility_collector):\n"
        "    compatibility_collector.record(requirement_id='DM-TASK-001', transport='jsonrpc', passed=True, level='MUST')\n"
        "@pytest.fixture\n"
        "def transport():\n"
        + ("    pytest.skip('no fixture transport')\n" if unavailable else "    return 'jsonrpc'\n")
        + "@pytest.mark.reference_scenario('artifact-text')\n"
        "@pytest.mark.parametrize('transport', ['jsonrpc'], indirect=True)\n"
        "def test_reference(transport):\n"
        "    '''DM-ART-001 is related, not tested by this fixture.'''\n"
        "    pytest.fail('reference text mismatch')\n",
        encoding="utf-8",
    )
    xml = tmp_path / "results.xml"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "tests.compatibility.conftest", str(probe), "-q",
         "--reference-scenario=artifact-text=run", f"--junitxml={xml}", f"--compatibility-report={tmp_path / 'compat'}"],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
    )
    assert result.returncode == (0 if unavailable else 1), result.stdout + result.stderr
    case = ET.parse(xml).find(".//testcase[@name='test_reference[jsonrpc]']")
    assert case is not None
    if unavailable:
        skipped = case.find("skipped")
        assert skipped is not None and "NOT_RUN" in skipped.attrib["message"] and "no fixture transport" in skipped.attrib["message"]
    else:
        assert case.find("failure") is not None
    report = json.loads((tmp_path / "compat.json").read_text(encoding="utf-8"))
    assert report["per_requirement"]["DM-ART-001"]["status"] == "NOT TESTED"


def test_nested_witnesses_are_checked_without_inspecting_application_data() -> None:
    """Validate history/status parts and every artifact, not arbitrary nested keys."""
    message = {"messageId": "m", "role": "ROLE_AGENT", "parts": [{"data": {"parts": [{}]}}]}
    payload = {"task": {"id": "t", "history": [message], "status": {"state": "TASK_STATE_COMPLETED", "message": message},
                        "artifacts": [{"parts": [{"text": "x", "url": "https://example.org"}]}]}}
    checks = observed_checks(payload, "http_json")
    assert not checks["DM-MSG-001"]
    assert checks["DM-ART-001"] == ["task.artifacts[0].artifactId: missing required value"]
    assert checks["DM-PART-001"] == ["task.artifacts[0].parts[0]: expected exactly one content variant"]


def test_report_does_not_award_an_artifact_pass_for_an_interrupted_task() -> None:
    """Exercise the actual MUST test and aggregator, not just the witness helper."""
    collector = CompatibilityCollector()
    schema = JSONSchemaValidator(ROOT / "specification" / "a2a.json")
    raw = {"task": {"id": "t", "status": {"state": "TASK_STATE_INPUT_REQUIRED", "message": {
        "messageId": "m", "role": "ROLE_AGENT", "parts": [{"text": "Which dates?"}],
    }}}}
    data_model.TestSendMessageResponseSchema().test_response_validates_against_schema(
        {"http_json": raw}, {"http_json": schema}, collector,
    )
    results = CompatibilityAggregator(collector).aggregate().per_requirement
    assert results["DM-ART-001"].status == "NOT TESTED"
    assert results["DM-MSG-001"].status == results["DM-PART-001"].status == results["DM-TASK-001"].status == "PASS"


def exercise(test: Callable[..., None], payload: dict[str, Any], transport: str) -> None:
    """Drive the actual fixture assertion with a synthetic transport response."""
    schema = JSONSchemaValidator(ROOT / "specification" / "a2a.json")
    validators = {"jsonrpc": JsonRpcResponseValidator(schema), "http_json": schema, "grpc": ProtoSchemaValidator()}
    raw = payload
    if transport == "jsonrpc":
        raw = {"jsonrpc": "2.0", "id": 1, "result": payload}
    elif transport == "grpc":
        raw = ParseDict(payload, a2a_pb2.SendMessageResponse())
    client = Mock()
    client.send_message.return_value = SimpleNamespace(raw_response=raw, success=True)
    test(transport, {transport: client}, validators)


def task(part: dict[str, Any]) -> dict[str, Any]:
    """Construct a completed task carrying one reference artifact."""
    return {"task": {"id": "t", "status": {"state": "TASK_STATE_COMPLETED"},
                     "artifacts": [{"artifactId": "a", "parts": [part]}]}}


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize(("test", "payload"), [
    (cases.TestTextArtifact().test_task_has_text_artifact, task({"text": "Generated text content"})),
    (cases.TestFileArtifact().test_task_has_file_artifact, task({"raw": "YQ==", "filename": "output.txt", "mediaType": "text/plain"})),
    (cases.TestFileUrlArtifact().test_task_has_file_url_artifact,
     task({"url": "https://example.org/file", "filename": "output.txt", "mediaType": "text/plain"})),
    (cases.TestDataArtifact().test_task_has_data_artifact, task({"data": {"key": "value", "count": 42}})),
    (cases.TestMessageResponse().test_returns_message_with_text_part,
     {"message": {"role": "ROLE_AGENT", "messageId": "m", "parts": [{"text": "Direct message response"}]}}),
])
def test_reference_outputs_still_exercised(test: Callable[..., None], payload: dict[str, Any], transport: str) -> None:
    """Every opted-in reference shape works on all supported transport representations."""
    exercise(test, payload, transport)


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_interrupted_is_distinct_from_invalid_or_wrong_content(transport: str) -> None:
    """Differentiate a valid interruption, an unexpected literal and a bad envelope."""
    case = cases.TestTextArtifact().test_task_has_text_artifact
    interrupted = {"task": {"id": "t", "status": {"state": "TASK_STATE_INPUT_REQUIRED"}}}
    with pytest.raises(pytest.fail.Exception, match="INPUT_REQUIRED"):
        exercise(case, interrupted, transport)
    with pytest.raises(AssertionError, match="Expected text"):
        exercise(case, task({"text": "a perfectly valid different answer"}), transport)
    with pytest.raises(AssertionError, match=r"exactly one|invalid response"):
        exercise(case, {}, transport)


@pytest.mark.parametrize("transport", ("jsonrpc", "http_json"))
def test_invalid_state_is_not_treated_as_input_required(transport: str) -> None:
    """Unknown JSON enum values fail validation before scenario assertions."""
    with pytest.raises(AssertionError, match="invalid response"):
        exercise(cases.TestTextArtifact().test_task_has_text_artifact,
                 {"task": {"id": "t", "status": {"state": "NOT_A_TASK_STATE"}}}, transport)


@pytest.mark.parametrize(("payload", "req"), [
    ({"task": {"id": "t", "status": {"state": 999}}}, "DM-TASK-002"),
    ({"message": {"messageId": "m", "role": 999, "parts": [{"text": "hello"}]}}, "DM-MSG-002"),
])
def test_unknown_numeric_proto_enum_never_receives_credit(payload: dict[str, Any], req: str) -> None:
    """Unknown numbers survive parsing a proto3 enum; they are not valid protocol states/roles."""
    raw = ParseDict(payload, a2a_pb2.SendMessageResponse())
    assert observed_checks(raw, "grpc")[req]
