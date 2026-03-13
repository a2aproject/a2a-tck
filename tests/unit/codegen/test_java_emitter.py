"""Tests for the Java code emitter (codegen.java_emitter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codegen.java_emitter import emit_java_project
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


class TestEmitJavaProject:
    """Tests for emit_java_project()."""

    def test_generates_expected_files(self, tmp_path: Path) -> None:
        """All four project files are generated."""
        generated = emit_java_project(_basic_scenarios(), tmp_path)
        names = {p.name for p in generated}

        assert "TckAgentExecutorProducer.java" in names
        assert "TckAgentCardProducer.java" in names
        assert "pom.xml" in names
        assert "application.properties" in names

    def test_executor_contains_prefix_routing(self, tmp_path: Path) -> None:
        """Generated executor routes on messageId prefix."""
        emit_java_project(_basic_scenarios(), tmp_path)
        executor = (
            tmp_path / "src" / "main" / "java"
            / "io" / "a2a" / "tck" / "sut"
            / "TckAgentExecutorProducer.java"
        )
        content = executor.read_text()

        assert 'messageId.startsWith("tck-send-001")' in content
        assert 'messageId.startsWith("tck-message-response")' in content
        assert 'messageId.startsWith("tck-reject-task")' in content

    def test_executor_contains_emitter_calls(self, tmp_path: Path) -> None:
        """Generated executor includes AgentEmitter method calls."""
        emit_java_project(_basic_scenarios(), tmp_path)
        executor = (
            tmp_path / "src" / "main" / "java"
            / "io" / "a2a" / "tck" / "sut"
            / "TckAgentExecutorProducer.java"
        )
        content = executor.read_text()

        assert "emitter.complete(A2A.toAgentMessage(" in content
        assert "emitter.sendMessage(" in content
        assert "emitter.requiresInput();" in content

    def test_agent_card_streaming_false(self, tmp_path: Path) -> None:
        """Agent card sets streaming=false when no streaming scenarios."""
        emit_java_project(_basic_scenarios(), tmp_path)
        card = (
            tmp_path / "src" / "main" / "java"
            / "io" / "a2a" / "tck" / "sut"
            / "TckAgentCardProducer.java"
        )
        content = card.read_text()
        assert ".streaming(false)" in content

    def test_agent_card_streaming_true(self, tmp_path: Path) -> None:
        """Agent card sets streaming=true when streaming scenarios present."""
        all_scenarios = _basic_scenarios() + _streaming_scenarios()
        emit_java_project(all_scenarios, tmp_path)
        card = (
            tmp_path / "src" / "main" / "java"
            / "io" / "a2a" / "tck" / "sut"
            / "TckAgentCardProducer.java"
        )
        content = card.read_text()
        assert ".streaming(true)" in content

    def test_pom_contains_a2a_dependency(self, tmp_path: Path) -> None:
        """Generated pom.xml includes a2a-java-sdk dependency."""
        emit_java_project(_basic_scenarios(), tmp_path)
        pom = tmp_path / "pom.xml"
        content = pom.read_text()
        assert "a2a-java-sdk-reference-jsonrpc" in content
        assert "io.github.a2asdk" in content
