"""Tests for the Python code emitter (codegen.python_emitter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codegen.model import (
    CompleteTask,
    MessageTrigger,
    RejectWithError,
    ReturnMessage,
    Scenario,
    StreamArtifact,
    StreamStatusUpdate,
    StreamingMessageTrigger,
    TextPartDef,
    UpdateTaskStatus,
    WaitForTimeout,
)
from codegen.python_emitter import emit_python_project


if TYPE_CHECKING:
    from pathlib import Path

WAIT_MULTIPLIER = 2


def _basic_scenarios() -> list[Scenario]:
    """A minimal set of scenarios for testing."""
    return [
        Scenario(
            name="Basic completion",
            trigger=MessageTrigger(prefix="tck-send-001"),
            actions=[CompleteTask(message="Hello")],
        ),
        Scenario(
            name="Return message",
            trigger=MessageTrigger(prefix="tck-message-response"),
            actions=[ReturnMessage(parts=[TextPartDef(text="Direct response")])],
        ),
        Scenario(
            name="Reject",
            trigger=MessageTrigger(prefix="tck-reject-task"),
            actions=[RejectWithError(error_type="rejected")],
        ),
        Scenario(
            name="Input required",
            trigger=MessageTrigger(prefix="tck-input-required"),
            actions=[UpdateTaskStatus(state="input_required")],
        ),
    ]


def _streaming_scenarios() -> list[Scenario]:
    """Scenarios including streaming triggers."""
    return [
        Scenario(
            name="Stream lifecycle",
            trigger=StreamingMessageTrigger(prefix="tck-stream-001"),
            actions=[
                StreamStatusUpdate(state="working"),
                StreamArtifact(parts=[TextPartDef(text="output")]),
                StreamStatusUpdate(state="completed"),
            ],
        ),
        Scenario(
            name="Long-running",
            trigger=StreamingMessageTrigger(prefix="test-resubscribe-message-id"),
            actions=[
                StreamStatusUpdate(state="working"),
                WaitForTimeout(multiplier=WAIT_MULTIPLIER),
                StreamStatusUpdate(state="completed"),
            ],
        ),
    ]


class TestEmitPythonProject:
    """Tests for emit_python_project()."""

    def test_generates_expected_files(self, tmp_path: Path) -> None:
        """Both project files are generated."""
        generated = emit_python_project(_basic_scenarios(), tmp_path)
        names = {p.name for p in generated}

        assert "sut_agent.py" in names
        assert "pyproject.toml" in names

    def test_executor_contains_prefix_routing(self, tmp_path: Path) -> None:
        """Generated executor routes on messageId prefix."""
        emit_python_project(_basic_scenarios(), tmp_path)
        content = (tmp_path / "sut_agent.py").read_text()

        assert "message_id.startswith('tck-send-001')" in content
        assert "message_id.startswith('tck-message-response')" in content
        assert "message_id.startswith('tck-reject-task')" in content

    def test_executor_contains_updater_calls(self, tmp_path: Path) -> None:
        """Generated executor includes TaskUpdater method calls."""
        emit_python_project(_basic_scenarios(), tmp_path)
        content = (tmp_path / "sut_agent.py").read_text()

        assert "await updater.complete(updater.new_agent_message(" in content
        assert "await event_queue.enqueue_event(updater.new_agent_message(" in content
        assert "await updater.requires_input()" in content

    def test_agent_card_streaming_false(self, tmp_path: Path) -> None:
        """Agent card sets streaming=False when no streaming scenarios."""
        emit_python_project(_basic_scenarios(), tmp_path)
        content = (tmp_path / "sut_agent.py").read_text()
        assert "streaming=False" in content

    def test_agent_card_streaming_true(self, tmp_path: Path) -> None:
        """Agent card sets streaming=True when streaming scenarios present."""
        all_scenarios = _basic_scenarios() + _streaming_scenarios()
        emit_python_project(all_scenarios, tmp_path)
        content = (tmp_path / "sut_agent.py").read_text()
        assert "streaming=True" in content

    def test_pyproject_contains_a2a_dependency(self, tmp_path: Path) -> None:
        """Generated pyproject.toml includes a2a-sdk dependency."""
        emit_python_project(_basic_scenarios(), tmp_path)
        content = (tmp_path / "pyproject.toml").read_text()
        assert "a2a-sdk" in content
