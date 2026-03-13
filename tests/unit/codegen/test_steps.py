"""Tests for the step registry (codegen.steps)."""

from __future__ import annotations

import pytest

from codegen.model import (
    AddArtifact,
    DataPartDef,
    FilePartDef,
    MessageTrigger,
    RejectWithError,
    ReturnMessage,
    ReturnTask,
    StreamArtifact,
    StreamStatusUpdate,
    StreamingMessageTrigger,
    TextPartDef,
    UpdateTaskStatus,
    WaitForTimeout,
)
from codegen.steps import resolve_action, resolve_trigger


WAIT_MULTIPLIER = 2


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


class TestResolveTrigger:
    """Tests for resolve_trigger()."""

    def test_message_trigger(self) -> None:
        """Unary message prefix resolves to MessageTrigger."""
        t = resolve_trigger('a message is received with prefix "tck-send-001"')
        assert t == MessageTrigger(prefix="tck-send-001")

    def test_streaming_message_trigger(self) -> None:
        """Streaming message prefix resolves to StreamingMessageTrigger."""
        t = resolve_trigger('a streaming message is received with prefix "tck-stream-001"')
        assert t == StreamingMessageTrigger(prefix="tck-stream-001")

    def test_unknown_trigger_raises(self) -> None:
        """Unknown When step raises ValueError."""
        with pytest.raises(ValueError, match="Unknown When step"):
            resolve_trigger("something unexpected happens")


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


class TestResolveAction:
    """Tests for resolve_action()."""

    def test_complete_task_with_text(self) -> None:
        """Complete with text resolves to ReturnTask with TextPartDef."""
        a = resolve_action('complete the task with a text part "Hello"')
        assert a == ReturnTask(parts=[TextPartDef(text="Hello")])

    def test_complete_task_bare(self) -> None:
        """Bare complete resolves to ReturnTask with no parts."""
        a = resolve_action("complete the task")
        assert a == ReturnTask()

    def test_add_artifact_text(self) -> None:
        """Text artifact resolves to AddArtifact with TextPartDef."""
        a = resolve_action('add an artifact with a text part "output"')
        assert a == AddArtifact(parts=[TextPartDef(text="output")])

    def test_add_artifact_file(self) -> None:
        """File artifact resolves to AddArtifact with FilePartDef."""
        a = resolve_action(
            'add an artifact with a file part named "out.txt" with media type "text/plain"'
        )
        assert a == AddArtifact(
            parts=[FilePartDef(name="out.txt", media_type="text/plain")]
        )

    def test_add_artifact_data(self) -> None:
        """Data artifact with docstring resolves to AddArtifact with DataPartDef."""
        a = resolve_action("add an artifact with a data part:", doc_string='{"k": 1}')
        assert a == AddArtifact(parts=[DataPartDef(json_content='{"k": 1}')])

    def test_return_message(self) -> None:
        """Return message resolves to ReturnMessage."""
        a = resolve_action('return a message with a text part "hi"')
        assert a == ReturnMessage(parts=[TextPartDef(text="hi")])

    def test_reject_with_error(self) -> None:
        """Reject step resolves to RejectWithError."""
        a = resolve_action('reject with error "rejected"')
        assert a == RejectWithError(error_type="rejected")

    def test_update_task_status(self) -> None:
        """Update status resolves to UpdateTaskStatus."""
        a = resolve_action('update the task status to "input_required"')
        assert a == UpdateTaskStatus(state="input_required")

    def test_stream_status_update(self) -> None:
        """Stream status update resolves to StreamStatusUpdate."""
        a = resolve_action('stream a status update to "working"')
        assert a == StreamStatusUpdate(state="working")

    def test_stream_artifact_text(self) -> None:
        """Stream artifact resolves to StreamArtifact."""
        a = resolve_action('stream an artifact with a text part "chunk"')
        assert a == StreamArtifact(parts=[TextPartDef(text="chunk")])

    def test_stream_artifact_file(self) -> None:
        """Stream file artifact resolves to StreamArtifact with FilePartDef."""
        a = resolve_action(
            'stream an artifact with a file part named "f.txt" with media type "text/plain"'
        )
        assert a == StreamArtifact(
            parts=[FilePartDef(name="f.txt", media_type="text/plain")]
        )

    def test_stream_artifact_chunk(self) -> None:
        """Stream artifact chunk resolves to StreamArtifact with append=True."""
        a = resolve_action('stream an artifact chunk with a text part "part1"')
        assert a == StreamArtifact(
            parts=[TextPartDef(text="part1")], append=True
        )

    def test_stream_final_artifact_chunk(self) -> None:
        """Stream final chunk resolves to StreamArtifact with last_chunk=True."""
        a = resolve_action('stream a final artifact chunk with a text part "last"')
        assert a == StreamArtifact(
            parts=[TextPartDef(text="last")], append=True, last_chunk=True,
        )

    def test_wait_for_timeout(self) -> None:
        """Wait for Nx timeout resolves to WaitForTimeout."""
        a = resolve_action("wait for 2x streaming timeout")
        assert a == WaitForTimeout(multiplier=WAIT_MULTIPLIER)

    def test_unknown_action_raises(self) -> None:
        """Unknown Then step raises ValueError."""
        with pytest.raises(ValueError, match="Unknown Then/And step"):
            resolve_action("do something unknown")
