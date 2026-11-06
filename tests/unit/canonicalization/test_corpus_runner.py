"""A reject vector must fail when the implementation crashes."""

from __future__ import annotations

import json
import runpy

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from tck.canonicalization.jcs import CanonicalizationError, canonicalize


if TYPE_CHECKING:
    from collections.abc import Callable


CORPUS_ROOT = Path(__file__).resolve().parents[3] / "conformance-vectors" / "a2a-jcs-v01"
RUNNER = runpy.run_path(str(CORPUS_ROOT / "run_python.py"))
REFUSAL_SPEC = "tck.canonicalization.jcs:CanonicalizationError"
CONFIGURATION_ERROR = 2
RFC8785_VECTOR_COUNT = json.loads((CORPUS_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))["targets"]["rfc8785"]["vectors"]
SURROGATE_VECTOR_IDS = ("A3-REJECT-011", "A3-REJECT-012", "A4-REJECT-013", "A4-REJECT-014", "A4-REJECT-015")


class DeclaredRefusalError(ValueError):
    """The adapter's declared input refusal."""


class UndeclaredRefusalError(DeclaredRefusalError):
    """A subclass the adapter did not declare."""


def raising(error: Exception) -> Callable[[Any], bytes]:
    """Return an implementation that raises the supplied error."""

    def implementation(value: Any) -> bytes:
        """Raise instead of producing canonical bytes."""
        del value
        raise error

    return implementation


@pytest.mark.parametrize(
    "error",
    [RuntimeError("crash"), UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogate"), UndeclaredRefusalError("unexpected")],
)
def test_undeclared_exception_is_an_error(error: Exception) -> None:
    """A base-class declaration does not hide an unexpected exception type."""
    kind, observed = RUNNER["run_function"](raising(error), None, (ValueError, DeclaredRefusalError))
    assert kind == "errored"
    assert observed is error


def test_declared_exception_is_a_refusal() -> None:
    """Only an explicitly named exception type counts as a refusal."""
    error = DeclaredRefusalError("invalid input")
    kind, observed = RUNNER["run_function"](raising(error), None, (DeclaredRefusalError,))
    assert kind == "refused"
    assert observed is error


@pytest.mark.parametrize("vector_id", SURROGATE_VECTOR_IDS)
def test_surrogate_crash_fails_the_actual_vector(vector_id: str) -> None:
    """The five cases from MolTrust's correction cannot pass on a codec crash."""
    manifest = json.loads((CORPUS_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    vectors = [json.loads((CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")) for entry in manifest["vectors"]]
    vector = next(vector for vector in vectors if vector["id"] == vector_id)
    error = UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogate")
    outcome, detail = RUNNER["check_vector"](vector, raising(error), (ValueError,))
    assert outcome == "errored"
    assert "UnicodeEncodeError" in detail


def test_external_adapter_requires_a_refusal_declaration(capsys: pytest.CaptureFixture[str]) -> None:
    """An omitted error contract stops the run before any score is produced."""
    assert RUNNER["main"](["--canonicalize", "tck.canonicalization.jcs:canonicalize"]) == CONFIGURATION_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--refusal is required" in captured.err


@pytest.mark.parametrize("spec", ["builtins:Exception", "builtins:BaseException", "builtins:str", "builtins:len"])
def test_invalid_refusal_declaration_is_a_configuration_error(spec: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid or catch-all declarations return status 2, not a runner traceback."""
    args = ["--canonicalize", "tck.canonicalization.jcs:canonicalize", "--refusal", spec]
    assert RUNNER["main"](args) == CONFIGURATION_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refusal must name" in captured.err


def test_report_records_the_exact_refusal_contract(capsys: pytest.CaptureFixture[str]) -> None:
    """A clean score includes the exception types and the matching rule."""
    args = ["--canonicalize", "tck.canonicalization.jcs:canonicalize", "--refusal", REFUSAL_SPEC]
    assert RUNNER["main"](args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refusal"] == [REFUSAL_SPEC]
    assert report["refusalMatch"] == "exact"
    assert report["targets"]["rfc8785"]["passed"] == RFC8785_VECTOR_COUNT
    assert report["targets"]["rfc8785"]["outcomes"]["errored"] == 0


def test_crash_is_reported_and_exits_nonzero(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A codec crash is retained as an error in the machine-readable score."""

    def crashes_on_surrogates(value: Any) -> bytes:
        """Replace proper refusals with the codec error found in the old run."""
        try:
            return canonicalize(value)
        except CanonicalizationError as exc:
            if "surrogate" in str(exc).lower():
                raise UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogate") from exc
            raise

    monkeypatch.setattr("tck.canonicalization.jcs.canonicalize", crashes_on_surrogates)
    args = [
        "--canonicalize",
        "tck.canonicalization.jcs:canonicalize",
        "--refusal",
        "builtins:ValueError",
        "--refusal",
        REFUSAL_SPEC,
    ]
    assert RUNNER["main"](args) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["targets"]["rfc8785"]["outcomes"]["errored"] == len(SURROGATE_VECTOR_IDS)
    assert report["targets"]["rfc8785"]["passed"] == RFC8785_VECTOR_COUNT - len(SURROGATE_VECTOR_IDS)
    assert sum(result["outcome"] == "errored" for result in report["results"]) == len(SURROGATE_VECTOR_IDS)
