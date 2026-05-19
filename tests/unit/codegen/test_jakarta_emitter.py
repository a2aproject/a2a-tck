"""Tests for the Jakarta code emitter (codegen.jakarta_emitter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codegen.jakarta_emitter import emit_jakarta_project
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


class TestEmitJakartaProject:
    """Tests for emit_jakarta_project()."""

    def test_generates_expected_files(self, tmp_path: Path) -> None:
        """All five project files are generated."""
        generated = emit_jakarta_project(_basic_scenarios(), tmp_path)
        names = {p.name for p in generated}

        assert "TckAgentExecutorProducer.java" in names
        assert "TckAgentCardProducer.java" in names
        assert "TckApplication.java" in names
        assert "beans.xml" in names
        assert "pom.xml" in names

    def test_executor_contains_prefix_routing(self, tmp_path: Path) -> None:
        """Generated executor routes on messageId prefix."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        executor = (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "jakarta" / "sdk" / "sut"
            / "TckAgentExecutorProducer.java"
        )
        content = executor.read_text()

        assert 'messageId.startsWith("tck-send-001")' in content
        assert 'messageId.startsWith("tck-message-response")' in content
        assert 'messageId.startsWith("tck-reject-task")' in content

    def test_executor_contains_emitter_calls(self, tmp_path: Path) -> None:
        """Generated executor includes AgentEmitter method calls."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        executor = (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "jakarta" / "sdk" / "sut"
            / "TckAgentExecutorProducer.java"
        )
        content = executor.read_text()

        assert "emitter.complete(A2A.toAgentMessage(" in content
        assert "emitter.sendMessage(" in content
        assert "emitter.requiresInput();" in content

    def test_agent_card_streaming_false(self, tmp_path: Path) -> None:
        """Agent card sets streaming=false when no streaming scenarios."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        card = (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "jakarta" / "sdk" / "sut"
            / "TckAgentCardProducer.java"
        )
        content = card.read_text()
        assert ".streaming(false)" in content

    def test_agent_card_streaming_true(self, tmp_path: Path) -> None:
        """Agent card sets streaming=true when streaming scenarios present."""
        all_scenarios = _basic_scenarios() + _streaming_scenarios()
        emit_jakarta_project(all_scenarios, tmp_path)
        card = (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "jakarta" / "sdk" / "sut"
            / "TckAgentCardProducer.java"
        )
        content = card.read_text()
        assert ".streaming(true)" in content

    def test_agent_card_has_separate_grpc_host(self, tmp_path: Path) -> None:
        """Agent card uses a separate gRPC host variable."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        card = (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "jakarta" / "sdk" / "sut"
            / "TckAgentCardProducer.java"
        )
        content = card.read_text()
        assert 'getEnvOrDefault("SUT_GRPC_HOST"' in content

    def test_pom_contains_jakarta_dependencies(self, tmp_path: Path) -> None:
        """Generated pom.xml includes Jakarta SDK dependencies and WAR packaging."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        pom = tmp_path / "pom.xml"
        content = pom.read_text()
        assert "<packaging>war</packaging>" in content
        assert "org.wildfly.a2a" in content
        assert "a2a-java-sdk-jakarta-jsonrpc" in content
        assert "a2a-java-sdk-jakarta-grpc" in content
        assert "wildfly-maven-plugin" in content

    def test_application_class_generated(self, tmp_path: Path) -> None:
        """TckApplication.java is a JAX-RS Application class."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        app = (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "jakarta" / "sdk" / "sut"
            / "TckApplication.java"
        )
        content = app.read_text()
        assert '@ApplicationPath("/")' in content
        assert "extends Application" in content

    def test_beans_xml_generated(self, tmp_path: Path) -> None:
        """beans.xml is generated with gRPC exclusion."""
        emit_jakarta_project(_basic_scenarios(), tmp_path)
        beans = (
            tmp_path / "src" / "main" / "resources" / "WEB-INF"
            / "beans.xml"
        )
        content = beans.read_text()
        assert "A2AServiceGrpc" in content
