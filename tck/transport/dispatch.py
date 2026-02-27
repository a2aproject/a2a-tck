"""Operation dispatcher for mapping requirements to transport client calls.

Routes an OperationType to the matching BaseTransportClient method,
using the requirement's ``sample_input`` dict to supply call arguments.

Each operation declares the client method name and which keys it expects
from ``sample_input``.  The dispatcher extracts those keys, forwards them
to the client, and skips if the required input is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import OperationType


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec
    from tck.transport.base import (
        BaseTransportClient,
        StreamingResponse,
        TransportResponse,
    )


@dataclass(frozen=True)
class _OperationDescriptor:
    """Describes how to call a client method for a given operation.

    Attributes:
        method: Name of the BaseTransportClient method to invoke.
        required_keys: Keys that *must* be present in ``sample_input``.
        optional_keys: Keys forwarded as keyword arguments when present.
    """

    method: str
    required_keys: list[str] = field(default_factory=list)
    optional_keys: list[str] = field(default_factory=list)


# Maps every OperationType to its client method and expected sample_input keys.
# Key names mirror the BaseTransportClient method signatures.
OPERATION_DESCRIPTORS: dict[OperationType, _OperationDescriptor] = {
    OperationType.SEND_MESSAGE: _OperationDescriptor(
        method="send_message",
        required_keys=["message"],
        optional_keys=["configuration", "metadata"],
    ),
    OperationType.SEND_STREAMING_MESSAGE: _OperationDescriptor(
        method="send_streaming_message",
        required_keys=["message"],
        optional_keys=["configuration", "metadata"],
    ),
    OperationType.GET_TASK: _OperationDescriptor(
        method="get_task",
        required_keys=["id"],
        optional_keys=["history_length"],
    ),
    OperationType.LIST_TASKS: _OperationDescriptor(
        method="list_tasks",
        required_keys=["context_id"],
        optional_keys=[
            "status",
            "page_size",
            "page_token",
            "history_length",
            "status_timestamp_after",
            "include_artifacts",
        ],
    ),
    OperationType.CANCEL_TASK: _OperationDescriptor(
        method="cancel_task",
        required_keys=["id"],
    ),
    OperationType.SUBSCRIBE_TO_TASK: _OperationDescriptor(
        method="subscribe_to_task",
        required_keys=["id"],
    ),
    OperationType.CREATE_PUSH_CONFIG: _OperationDescriptor(
        method="create_push_notification_config",
        required_keys=["task_id", "config_id", "config"],
    ),
    OperationType.GET_PUSH_CONFIG: _OperationDescriptor(
        method="get_push_notification_config",
        required_keys=["task_id", "id"],
    ),
    OperationType.LIST_PUSH_CONFIGS: _OperationDescriptor(
        method="list_push_notification_configs",
        required_keys=["task_id"],
        optional_keys=["page_size", "page_token"],
    ),
    OperationType.DELETE_PUSH_CONFIG: _OperationDescriptor(
        method="delete_push_notification_config",
        required_keys=["task_id", "id"],
    ),
    OperationType.GET_EXTENDED_AGENT_CARD: _OperationDescriptor(
        method="get_extended_agent_card",
    ),
}


def execute_operation(
    client: BaseTransportClient,
    requirement: RequirementSpec,
) -> TransportResponse | StreamingResponse:
    """Execute the operation associated with a requirement on the given client.

    The requirement's ``sample_input`` dict supplies every argument.
    Required keys that are missing cause a ``pytest.skip`` so the test
    is clearly marked as "not yet runnable" rather than silently passing
    or failing with a confusing error.

    Args:
        client: The transport client to use.
        requirement: The requirement whose operation to execute.

    Returns:
        The transport response.

    Raises:
        pytest.skip: If the requirement has no operation (cross-cutting),
                     the operation is unknown, or required sample_input
                     keys are missing.
    """
    if requirement.operation is None:
        # Provide specific skip reasons based on tags
        if "not-automatable" in requirement.tags:
            pytest.skip(
                f"{requirement.id} is not automatable (requires manual verification)"
            )
        if "multi-operation" in requirement.tags:
            pytest.skip(
                f"{requirement.id} requires multi-operation orchestration"
            )
        pytest.skip(
            f"{requirement.id} is a cross-cutting requirement (no operation)"
        )

    descriptor = OPERATION_DESCRIPTORS.get(requirement.operation)
    if descriptor is None:
        pytest.skip(
            f"{requirement.id} has unhandled operation: "
            f"{requirement.operation.value}"
        )

    sample = requirement.sample_input

    # Check that all required keys are present
    missing = [k for k in descriptor.required_keys if k not in sample]
    if missing:
        pytest.skip(
            f"{requirement.id}: sample_input missing required keys "
            f"{missing} for {requirement.operation.value}"
        )

    # Build positional args from required keys (order matters)
    args: list[Any] = [sample[k] for k in descriptor.required_keys]

    # Build keyword args from optional keys
    kwargs: dict[str, Any] = {
        k: sample[k] for k in descriptor.optional_keys if k in sample
    }

    method = getattr(client, descriptor.method)
    return method(*args, **kwargs)
