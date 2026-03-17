"""Python code emitter for a2a-python SDK.

Generates a complete runnable Python project from parsed Scenario objects
using Jinja2 templates stored in ``codegen/a2a-python/``.
"""

from __future__ import annotations

import json
import os

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codegen.model import (
    AddArtifact,
    CompleteTask,
    DataPartDef,
    FilePartDef,
    FileUrlPartDef,
    MessageTrigger,
    PartDef,
    RejectWithError,
    ReturnMessage,
    Scenario,
    StreamingMessageTrigger,
    TextPartDef,
    UpdateTaskStatus,
    WaitForTimeout,
)


_TEMPLATES_DIR = Path(__file__).parent / "a2a-python"

_DEFAULT_A2A_PYTHON_SDK_VERSION = "0.3.0"
_DEFAULT_A2A_PYTHON_SDK_PATH = "../../../a2a-python"

_STREAMING_TIMEOUT_S = 2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_python_project(scenarios: list[Scenario], output_dir: Path) -> list[Path]:
    """Generate a complete a2a-python SUT project under *output_dir*.

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

    a2a_python_sdk_version = os.environ.get(
        "A2A_PYTHON_SDK_VERSION", _DEFAULT_A2A_PYTHON_SDK_VERSION,
    )
    a2a_python_sdk_path = os.environ.get(
        "A2A_PYTHON_SDK_PATH", _DEFAULT_A2A_PYTHON_SDK_PATH,
    )

    context = {
        "handlers": handlers,
        "has_streaming": has_streaming,
        "a2a_python_sdk_version": a2a_python_sdk_version,
        "a2a_python_sdk_path": a2a_python_sdk_path,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for template_name, filename in [
        ("sut_agent.py.j2", "sut_agent.py"),
        ("pyproject.toml.j2", "pyproject.toml"),
    ]:
        generated.append(_render(env, template_name, context, output_dir / filename))

    return generated


# ---------------------------------------------------------------------------
# Handler building (Scenario → Python code)
# ---------------------------------------------------------------------------


@dataclass
class _Handler:
    """Pre-rendered handler for a single messageId prefix."""

    prefix: str
    python_code: str
    raises: bool = False


def _build_handlers(scenarios: list[Scenario]) -> list[_Handler]:
    """Convert scenarios to pre-rendered Python code handlers.

    Handlers are sorted by prefix length (longest first) so that more
    specific prefixes match before less specific ones in the generated
    ``startswith`` chain.
    """
    handlers: list[_Handler] = []
    for scenario in scenarios:
        trigger = scenario.trigger
        if isinstance(trigger, (MessageTrigger, StreamingMessageTrigger)):
            code, raises = _render_actions(scenario)
            handlers.append(_Handler(prefix=trigger.prefix, python_code=code, raises=raises))
    handlers.sort(key=lambda h: len(h.prefix), reverse=True)
    return handlers


def _render_actions(scenario: Scenario) -> tuple[str, bool]:
    """Render a scenario's actions as Python statements.

    Terminal actions (CompleteTask, RejectWithError) are deferred to the end
    so that artifacts and messages are emitted first.

    Returns ``(python_code, raises)`` where *raises* is True when the handler
    ends with a ``raise`` (so the template can omit the unreachable ``return``).
    """
    immediate: list[str] = []
    deferred: list[str] = []
    has_raise = False

    for action in scenario.actions:
        python_lines = _action_to_python(action)
        if isinstance(action, (CompleteTask, RejectWithError)):
            deferred.extend(python_lines)
            if isinstance(action, RejectWithError):
                has_raise = True
        else:
            immediate.extend(python_lines)

    return "\n".join(immediate + deferred), has_raise


def _action_to_python(action: object) -> list[str]:
    """Convert a single Action to Python statement lines."""
    if isinstance(action, CompleteTask):
        if action.message:
            return [f"await updater.complete(updater.new_agent_message([Part(text={_py_string(action.message)})]))"]
        if action.parts:
            return [f"await updater.complete(updater.new_agent_message([{_parts_to_python(action.parts)}]))"]
        return ["await updater.complete()"]

    if isinstance(action, AddArtifact):
        kwargs = [f"parts=[{_parts_to_python(action.parts)}]"]
        if action.append:
            kwargs.append(f"append={action.append}")
        if action.last_chunk:
            kwargs.append(f"last_chunk={action.last_chunk}")
        return [f"await updater.add_artifact({', '.join(kwargs)})"]

    if isinstance(action, ReturnMessage):
        return [f"await event_queue.enqueue_event(updater.new_agent_message([{_parts_to_python(action.parts)}]))"]

    if isinstance(action, RejectWithError):
        return [_error_to_python(action.error_type)]

    if isinstance(action, UpdateTaskStatus):
        return [_status_to_python(action.state)]

    if isinstance(action, WaitForTimeout):
        seconds = action.multiplier * _STREAMING_TIMEOUT_S
        return [f"await asyncio.sleep({seconds})"]

    msg = f"Unsupported action type: {type(action).__name__}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Python code fragment helpers
# ---------------------------------------------------------------------------


_STATE_MAP = {
    "submitted": "await updater.submit()",
    "working": "await updater.start_work()",
    "completed": "await updater.complete()",
    "failed": "await updater.failed()",
    "canceled": "await updater.cancel()",
    "rejected": "await updater.reject()",
    "input_required": "await updater.requires_input()",
    "auth_required": "await updater.requires_auth()",
}

_ERROR_MAP = {
    "rejected": "raise A2AError('rejected')",
    "unsupported_operation": "raise UnsupportedOperationError()",
    "task_not_cancelable": "raise TaskNotCancelableError()",
}


def _status_to_python(state: str) -> str:
    """Map a task state name to the corresponding TaskUpdater call."""
    python = _STATE_MAP.get(state)
    if python is None:
        msg = f"Unknown task state: {state!r}"
        raise ValueError(msg)
    return python


def _error_to_python(error_type: str) -> str:
    """Map an error type name to a Python raise statement."""
    python = _ERROR_MAP.get(error_type)
    if python is None:
        msg = f"Unknown error type: {error_type!r}"
        raise ValueError(msg)
    return python


def _parts_to_python(parts: list[PartDef]) -> str:
    """Render a list of part definitions as comma-separated Python expressions."""
    return ", ".join(_single_part_to_python(p) for p in parts)


def _single_part_to_python(part: PartDef) -> str:
    """Render a single part definition as a Python constructor expression."""
    if isinstance(part, TextPartDef):
        return f"Part(text={_py_string(part.text)})"

    if isinstance(part, FilePartDef):
        return (
            f"Part(raw=b'tck', "
            f"media_type={_py_string(part.media_type)}, "
            f"filename={_py_string(part.name)})"
        )

    if isinstance(part, FileUrlPartDef):
        return (
            f"Part(url={_py_string(part.url)}, "
            f"media_type={_py_string(part.media_type)}, "
            f"filename={_py_string(part.name)})"
        )

    if isinstance(part, DataPartDef):
        return f"Part(data=json_format.ParseDict({part.json_content}, Value()))"

    msg = f"Unknown part type: {type(part).__name__}"
    raise ValueError(msg)


def _py_string(value: str) -> str:
    """Escape a Python string as a string literal."""
    return json.dumps(value)


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def _render(env: Environment, template_name: str, context: dict, dest: Path) -> Path:
    """Render a single template to *dest* and return the path."""
    template = env.get_template(template_name)
    dest.write_text(template.render(**context))
    return dest
