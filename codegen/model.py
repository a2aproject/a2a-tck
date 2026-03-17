"""Data model for parsed Gherkin scenarios.

Defines the intermediate representation used between the Gherkin parser
and the language-specific code emitters.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Part definitions (content carried by artifacts or messages)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TextPartDef:
    """A text content part."""

    text: str


@dataclass(frozen=True)
class FilePartDef:
    """A file content part (inline bytes)."""

    name: str
    media_type: str


@dataclass(frozen=True)
class FileUrlPartDef:
    """A file content part (URL reference)."""

    url: str
    name: str
    media_type: str


@dataclass(frozen=True)
class DataPartDef:
    """A structured data content part (JSON)."""

    json_content: str


PartDef = TextPartDef | FilePartDef | FileUrlPartDef | DataPartDef


# ---------------------------------------------------------------------------
# Triggers (When steps)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MessageTrigger:
    """Triggered when a unary message is received with a matching prefix."""

    prefix: str


@dataclass(frozen=True)
class StreamingMessageTrigger:
    """Triggered when a streaming message is received with a matching prefix."""

    prefix: str


Trigger = MessageTrigger | StreamingMessageTrigger


# ---------------------------------------------------------------------------
# Actions (Then/And steps)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompleteTask:
    """Complete the task, optionally with a message string or parts."""

    message: str | None = None
    parts: list[PartDef] = field(default_factory=list)


@dataclass(frozen=True)
class AddArtifact:
    """Add an artifact to the task."""

    parts: list[PartDef]
    append: bool = False
    last_chunk: bool = False


@dataclass(frozen=True)
class ReturnMessage:
    """Return a Message (not a Task) response."""

    parts: list[PartDef]


@dataclass(frozen=True)
class RejectWithError:
    """Reject the request with an error."""

    error_type: str


@dataclass(frozen=True)
class UpdateTaskStatus:
    """Update the task status to a specific state."""

    state: str


@dataclass(frozen=True)
class StreamStatusUpdate:
    """Stream a task status update event."""

    state: str


@dataclass(frozen=True)
class StreamArtifact:
    """Stream an artifact update event."""

    parts: list[PartDef]
    append: bool = False
    last_chunk: bool = False


@dataclass(frozen=True)
class WaitForTimeout:
    """Wait for N times the streaming timeout."""

    multiplier: int


Action = (
    CompleteTask
    | AddArtifact
    | ReturnMessage
    | RejectWithError
    | UpdateTaskStatus
    | StreamStatusUpdate
    | StreamArtifact
    | WaitForTimeout
)


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    """A parsed Gherkin scenario with trigger and actions."""

    name: str
    trigger: Trigger
    actions: list[Action]
