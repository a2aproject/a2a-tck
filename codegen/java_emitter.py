"""Java code emitter for a2a-java SDK (Quarkus).

Generates a complete runnable Java project from parsed Scenario objects
using Jinja2 templates stored in ``codegen/a2a-java/``.
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codegen.model import (
    AddArtifact,
    DataPartDef,
    FilePartDef,
    MessageTrigger,
    PartDef,
    RejectWithError,
    ReturnMessage,
    ReturnTask,
    Scenario,
    StreamArtifact,
    StreamStatusUpdate,
    StreamingMessageTrigger,
    TextPartDef,
    UpdateTaskStatus,
    WaitForTimeout,
)


_TEMPLATES_DIR = Path(__file__).parent / "a2a-java"

_JAVA_PACKAGE = "io.a2a.tck.sut"
_JAVA_PACKAGE_DIR = _JAVA_PACKAGE.replace(".", "/")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_java_project(scenarios: list[Scenario], output_dir: Path) -> list[Path]:
    """Generate a complete Quarkus + a2a-java project under *output_dir*.

    Returns the list of generated file paths.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    handlers = _build_handlers(scenarios)
    has_streaming = any(
        isinstance(s.trigger, StreamingMessageTrigger) for s in scenarios
    )

    context = {
        "handlers": handlers,
        "has_streaming": has_streaming,
        "package": _JAVA_PACKAGE,
    }

    generated: list[Path] = []

    # Java sources
    java_src = output_dir / "src" / "main" / "java" / _JAVA_PACKAGE_DIR
    java_src.mkdir(parents=True, exist_ok=True)

    for template_name, filename in [
        ("TckAgentExecutorProducer.java.j2", "TckAgentExecutorProducer.java"),
        ("TckAgentCardProducer.java.j2", "TckAgentCardProducer.java"),
    ]:
        generated.append(_render(env, template_name, context, java_src / filename))

    # Resources
    resources = output_dir / "src" / "main" / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    generated.append(
        _render(env, "application.properties.j2", context, resources / "application.properties")
    )

    # Build file
    generated.append(_render(env, "pom.xml.j2", context, output_dir / "pom.xml"))

    return generated


# ---------------------------------------------------------------------------
# Handler building (Scenario → Java code)
# ---------------------------------------------------------------------------


@dataclass
class _Handler:
    """Pre-rendered handler for a single messageId prefix."""

    prefix: str
    java_code: str
    throws: bool = False


def _build_handlers(scenarios: list[Scenario]) -> list[_Handler]:
    """Convert scenarios to pre-rendered Java code handlers."""
    handlers: list[_Handler] = []
    for scenario in scenarios:
        trigger = scenario.trigger
        if isinstance(trigger, (MessageTrigger, StreamingMessageTrigger)):
            code, throws = _render_actions(scenario)
            handlers.append(_Handler(prefix=trigger.prefix, java_code=code, throws=throws))
    return handlers


def _render_actions(scenario: Scenario) -> tuple[str, bool]:
    """Render a scenario's actions as Java statements.

    Terminal actions (ReturnTask, RejectWithError) are deferred to the end
    so that artifacts and messages are emitted first.

    Returns ``(java_code, throws)`` where *throws* is True when the handler
    ends with a ``throw`` (so the template can omit the unreachable ``return``).
    """
    immediate: list[str] = []
    deferred: list[str] = []
    has_throw = False

    for action in scenario.actions:
        java_lines = _action_to_java(action)
        if isinstance(action, (ReturnTask, RejectWithError)):
            deferred.extend(java_lines)
            if isinstance(action, RejectWithError):
                has_throw = True
        else:
            immediate.extend(java_lines)

    return "\n".join(immediate + deferred), has_throw


def _action_to_java(action: object) -> list[str]:
    """Convert a single Action to Java statement lines."""
    if isinstance(action, ReturnTask):
        lines: list[str] = []
        if action.parts:
            lines.append(f"emitter.sendMessage({_parts_to_java(action.parts)});")
        lines.append("emitter.complete();")
        return lines

    if isinstance(action, AddArtifact):
        args = [_parts_to_java(action.parts)]
        # artifactId, name, metadata
        args.extend(["null", "null", "null"])
        if action.append or action.last_chunk:
            args.append(str(action.append).lower())
            args.append(str(action.last_chunk).lower())
        return [f"emitter.addArtifact({', '.join(args)});"]

    if isinstance(action, ReturnMessage):
        return [f"emitter.sendMessage({_parts_to_java(action.parts)});"]

    if isinstance(action, RejectWithError):
        return [_error_to_java(action.error_type)]

    if isinstance(action, UpdateTaskStatus):
        return [_status_to_java(action.state)]

    if isinstance(action, StreamStatusUpdate):
        return [_status_to_java(action.state)]

    if isinstance(action, StreamArtifact):
        args = [_parts_to_java(action.parts)]
        args.extend(["null", "null", "null"])
        if action.append or action.last_chunk:
            args.append(str(action.append).lower())
            args.append(str(action.last_chunk).lower())
        return [f"emitter.addArtifact({', '.join(args)});"]

    if isinstance(action, WaitForTimeout):
        ms = action.multiplier * 2000
        return [
            f"try {{ Thread.sleep({ms}); }}"
            " catch (InterruptedException e) { Thread.currentThread().interrupt(); }",
        ]

    msg = f"Unsupported action type: {type(action).__name__}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Java code fragment helpers
# ---------------------------------------------------------------------------


_STATE_MAP = {
    "submitted": "emitter.submit();",
    "working": "emitter.startWork();",
    "completed": "emitter.complete();",
    "failed": "emitter.fail();",
    "canceled": "emitter.cancel();",
    "rejected": "emitter.reject();",
    "input_required": "emitter.requiresInput();",
    "auth_required": "emitter.requiresAuth();",
}

_ERROR_MAP = {
    "rejected": 'throw new A2AError(-1, "rejected", null);',
    "unsupported_operation": "throw new io.a2a.spec.UnsupportedOperationError();",
    "task_not_cancelable": "throw new TaskNotCancelableError();",
}


def _status_to_java(state: str) -> str:
    """Map a task state name to the corresponding AgentEmitter call."""
    java = _STATE_MAP.get(state)
    if java is None:
        msg = f"Unknown task state: {state!r}"
        raise ValueError(msg)
    return java


def _error_to_java(error_type: str) -> str:
    """Map an error type name to a Java throw statement."""
    java = _ERROR_MAP.get(error_type)
    if java is None:
        msg = f"Unknown error type: {error_type!r}"
        raise ValueError(msg)
    return java


def _parts_to_java(parts: list[PartDef]) -> str:
    """Render a list of part definitions as a Java List.of(...) expression."""
    if len(parts) == 1:
        return _single_part_to_java(parts[0])
    fragments = [_single_part_to_java(p) for p in parts]
    return f"List.of({', '.join(fragments)})"


def _single_part_to_java(part: PartDef) -> str:
    """Render a single part definition as a Java expression."""
    if isinstance(part, TextPartDef):
        return f'List.of(new TextPart({_java_string(part.text)}))'

    if isinstance(part, FilePartDef):
        return (
            f"List.of(new FilePart(new FileWithBytes("
            f"{_java_string(part.media_type)}, "
            f"{_java_string(part.name)}, "
            f'"dGNr")))'  # base64 "tck"
        )

    if isinstance(part, DataPartDef):
        return f"List.of(new DataPart({_java_string(part.json_content)}))"

    msg = f"Unknown part type: {type(part).__name__}"
    raise ValueError(msg)


def _java_string(value: str) -> str:
    """Escape a Python string as a Java string literal."""
    return json.dumps(value)


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def _render(env: Environment, template_name: str, context: dict, dest: Path) -> Path:
    """Render a single template to *dest* and return the path."""
    template = env.get_template(template_name)
    dest.write_text(template.render(**context))
    return dest
