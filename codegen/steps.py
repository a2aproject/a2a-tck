"""Step registry mapping Gherkin step text to Action objects.

Each entry pairs a compiled regex with a factory function that
produces the corresponding Action from the captured groups.
"""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

from codegen.model import (
    AddArtifact,
    CompleteTask,
    DataPartDef,
    FilePartDef,
    FileUrlPartDef,
    MessageTrigger,
    RejectWithError,
    ReturnMessage,
    StreamArtifact,
    StreamStatusUpdate,
    StreamingMessageTrigger,
    TextPartDef,
    UpdateTaskStatus,
    WaitForTimeout,
)


if TYPE_CHECKING:
    from codegen.model import Action, Trigger


# ---------------------------------------------------------------------------
# When-step registry  (pattern → Trigger factory)
# ---------------------------------------------------------------------------

_WHEN_STEPS: list[tuple[re.Pattern[str], callable]] = [
    (
        re.compile(r'^a message is received with prefix "(.+)"$'),
        lambda m, _ds: MessageTrigger(prefix=m.group(1)),
    ),
    (
        re.compile(r'^a streaming message is received with prefix "(.+)"$'),
        lambda m, _ds: StreamingMessageTrigger(prefix=m.group(1)),
    ),
]

# ---------------------------------------------------------------------------
# Then/And-step registry  (pattern → Action factory)
# ---------------------------------------------------------------------------

_THEN_STEPS: list[tuple[re.Pattern[str], callable]] = [
    # --- Task completion ---
    (
        re.compile(r'^complete the task with the message "(.+)"$'),
        lambda m, _ds: CompleteTask(message=m.group(1)),
    ),
    (
        re.compile(r'^complete the task with a text part "(.+)"$'),
        lambda m, _ds: CompleteTask(parts=[TextPartDef(text=m.group(1))]),
    ),
    (
        re.compile(r'^complete the task$'),
        lambda _m, _ds: CompleteTask(),
    ),
    # --- Artifacts ---
    (
        re.compile(r'^add an artifact with a text part "(.+)"$'),
        lambda m, _ds: AddArtifact(parts=[TextPartDef(text=m.group(1))]),
    ),
    (
        re.compile(
            r'^add an artifact with a file part named "(.+)" with media type "(.+)"$'
        ),
        lambda m, _ds: AddArtifact(parts=[FilePartDef(name=m.group(1), media_type=m.group(2))]),
    ),
    (
        re.compile(
            r'^add an artifact with a file url "(.+)" named "(.+)" with media type "(.+)"$'
        ),
        lambda m, _ds: AddArtifact(parts=[FileUrlPartDef(url=m.group(1), name=m.group(2), media_type=m.group(3))]),
    ),
    (
        re.compile(r'^add an artifact with a data part:$'),
        lambda _m, ds: AddArtifact(parts=[DataPartDef(json_content=ds)]),
    ),
    # --- Message response ---
    (
        re.compile(r'^return a message with a text part "(.+)"$'),
        lambda m, _ds: ReturnMessage(parts=[TextPartDef(text=m.group(1))]),
    ),
    # --- Error rejection ---
    (
        re.compile(r'^reject with error "(.+)"$'),
        lambda m, _ds: RejectWithError(error_type=m.group(1)),
    ),
    # --- Task status ---
    (
        re.compile(r'^update the task status to "(.+)"$'),
        lambda m, _ds: UpdateTaskStatus(state=m.group(1)),
    ),
    # --- Streaming ---
    (
        re.compile(r'^stream a status update to "(.+)"$'),
        lambda m, _ds: StreamStatusUpdate(state=m.group(1)),
    ),
    (
        re.compile(r'^stream an artifact with a text part "(.+)"$'),
        lambda m, _ds: StreamArtifact(parts=[TextPartDef(text=m.group(1))]),
    ),
    (
        re.compile(
            r'^stream an artifact with a file part named "(.+)" with media type "(.+)"$'
        ),
        lambda m, _ds: StreamArtifact(parts=[FilePartDef(name=m.group(1), media_type=m.group(2))]),
    ),
    (
        re.compile(r'^stream an artifact chunk with a text part "(.+)"$'),
        lambda m, _ds: StreamArtifact(parts=[TextPartDef(text=m.group(1))], append=True),
    ),
    (
        re.compile(r'^stream a final artifact chunk with a text part "(.+)"$'),
        lambda m, _ds: StreamArtifact(
            parts=[TextPartDef(text=m.group(1))], append=True, last_chunk=True,
        ),
    ),
    (
        re.compile(r'^wait for (\d+)x streaming timeout$'),
        lambda m, _ds: WaitForTimeout(multiplier=int(m.group(1))),
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_trigger(text: str, doc_string: str | None = None) -> Trigger:
    """Resolve a When-step text to a Trigger object.

    Raises ``ValueError`` if no matching pattern is found.
    """
    for pattern, factory in _WHEN_STEPS:
        match = pattern.match(text)
        if match:
            return factory(match, doc_string)
    msg = f"Unknown When step: {text!r}"
    raise ValueError(msg)


def resolve_action(text: str, doc_string: str | None = None) -> Action:
    """Resolve a Then/And-step text to an Action object.

    Raises ``ValueError`` if no matching pattern is found.
    """
    for pattern, factory in _THEN_STEPS:
        match = pattern.match(text)
        if match:
            return factory(match, doc_string)
    msg = f"Unknown Then/And step: {text!r}"
    raise ValueError(msg)
