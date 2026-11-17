"""Witnesses for data-model checks on a schema-validated SendMessage reply."""

from __future__ import annotations

from typing import Any

from google.protobuf.json_format import MessageToDict

from specification.generated import a2a_pb2


_TASK_STATES = frozenset(a2a_pb2.TaskState.keys())


def observed_checks(raw: Any, transport: str) -> dict[str, list[str]]:
    """Return only exercised requirements and their errors, never walk user data."""
    payload = MessageToDict(raw) if transport == "grpc" else raw["result"] if transport == "jsonrpc" else raw
    out: dict[str, list[str]] = {"DM-SERIAL-004": []}
    if len({"task", "message"}.intersection(payload)) != 1:
        out["DM-SERIAL-004"].append("expected exactly one task or message")
        return out

    def required(req: str, obj: dict, fields: tuple[str, ...], path: str) -> None:
        errors = out.setdefault(req, [])
        for field in fields:
            if field not in obj or obj[field] in (None, "", [], {}):
                errors.append(f"{path}.{field}: missing required value")

    def parts(obj: dict, path: str) -> None:
        for i, part in enumerate(obj.get("parts", [])):
            errors = out.setdefault("DM-PART-001", [])
            if len({"text", "raw", "url", "data"}.intersection(part)) != 1:
                errors.append(f"{path}.parts[{i}]: expected exactly one content variant")

    def message(obj: dict, path: str) -> None:
        required("DM-MSG-001", obj, ("messageId", "role", "parts"), path)
        if "role" in obj:
            errors = out.setdefault("DM-MSG-002", [])
            if obj["role"] not in ("ROLE_USER", "ROLE_AGENT"):
                errors.append(f"{path}.role: unknown or unspecified role")
        parts(obj, path)

    if "message" in payload:
        message(payload["message"], "message")
    else:
        task = payload["task"]
        required("DM-TASK-001", task, ("id", "status"), "task")
        status = task.get("status", {})
        required("DM-STATUS-001", status, ("state",), "task.status")
        if "state" in status:
            out["DM-TASK-002"] = []
            # Protobuf permits unknown numeric enum values on the wire.
            if status["state"] not in _TASK_STATES:
                error = "task.status.state: unknown task state"
                out["DM-TASK-002"].append(error)
                out["DM-STATUS-001"].append(error)
        if "message" in status:
            message(status["message"], "task.status.message")
        for i, item in enumerate(task.get("history", [])):
            message(item, f"task.history[{i}]")
        for i, artifact in enumerate(task.get("artifacts", [])):
            path = f"task.artifacts[{i}]"
            required("DM-ART-001", artifact, ("artifactId", "parts"), path)
            parts(artifact, path)
    out["DM-SERIAL-004"].extend(
        error for req in ("DM-MSG-001", "DM-TASK-001", "DM-ART-001", "DM-STATUS-001") for error in out.get(req, [])
    )
    return out
