"""Streaming requirements from A2A specification Sections 3.5 and 4.2.

Covers: Event ordering, lifecycle, terminal state, SubscribeToTask
first-event semantics, multiple streams per task.
"""

from __future__ import annotations

from tck.requirements.base import (
    SPEC_BASE,
    SUBSCRIBE_TO_TASK_BINDING,
    TASK_NOT_FOUND_ERROR,
    OperationType,
    RequirementLevel,
    RequirementSpec,
    tck_id,
)
from tck.requirements.tags import (
    ERROR,
    MULTI_OPERATION,
    MULTI_STREAM,
    ORDERING,
    STREAMING,
    SUBSCRIBE,
)


STREAMING_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="STREAM-ORDER-001",
        section="3.5.2",
        title="Events delivered in generation order",
        level=RequirementLevel.MUST,
        description=(
            "All implementations MUST deliver events in the order they were "
            "generated. Events MUST NOT be reordered during transmission."
        ),
        expected_behavior="Events arrive in generation order",
        spec_url=f"{SPEC_BASE}352-streaming-event-delivery",
        tags=[STREAMING, ORDERING, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="STREAM-ORDER-002",
        section="3.5.2",
        title="Events broadcast to all active streams",
        level=RequirementLevel.MUST,
        description=(
            "When multiple streams are active for a task, events MUST be "
            "broadcast to all active streams for that task."
        ),
        expected_behavior="All active streams receive the same events",
        spec_url=f"{SPEC_BASE}352-streaming-event-delivery",
        tags=[STREAMING, MULTI_STREAM, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="STREAM-ORDER-003",
        section="3.5.2",
        title="Each stream receives same events in same order",
        level=RequirementLevel.MUST,
        description=(
            "Each stream MUST receive the same events in the same order."
        ),
        expected_behavior="Event ordering consistent across all streams",
        spec_url=f"{SPEC_BASE}352-streaming-event-delivery",
        tags=[STREAMING, MULTI_STREAM, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="STREAM-ORDER-004",
        section="3.5.2",
        title="Closing one stream does not affect others",
        level=RequirementLevel.MUST,
        description=(
            "Closing one stream MUST NOT affect other active streams for "
            "the same task."
        ),
        expected_behavior="Other streams continue when one closes",
        spec_url=f"{SPEC_BASE}352-streaming-event-delivery",
        tags=[STREAMING, MULTI_STREAM, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="STREAM-SUB-001",
        section="3.1.6",
        title="SubscribeToTask returns Task as first event",
        level=RequirementLevel.MUST,
        description=(
            "The SubscribeToTask operation MUST return a Task object as the "
            "first event in the stream, representing the current state of "
            "the task at the time of subscription."
        ),
        operation=OperationType.SUBSCRIBE_TO_TASK,
        binding=SUBSCRIBE_TO_TASK_BINDING,
        proto_request_type="SubscribeToTaskRequest",
        proto_response_type="StreamResponse",
        expected_behavior="First event is a Task object with current state",
        spec_url=f"{SPEC_BASE}316-subscribe-to-task",
        tags=[STREAMING, SUBSCRIBE, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="STREAM-SUB-002",
        section="3.1.6",
        title="SubscribeToTask stream terminates at terminal state",
        level=RequirementLevel.MUST,
        description=(
            "The SubscribeToTask stream MUST terminate when the task reaches "
            "a terminal state (completed, failed, canceled, or rejected)."
        ),
        operation=OperationType.SUBSCRIBE_TO_TASK,
        binding=SUBSCRIBE_TO_TASK_BINDING,
        proto_request_type="SubscribeToTaskRequest",
        proto_response_type="StreamResponse",
        expected_behavior="Stream closes at terminal state",
        spec_url=f"{SPEC_BASE}316-subscribe-to-task",
        tags=[STREAMING, SUBSCRIBE, MULTI_OPERATION],

    ),
    RequirementSpec(
        id="STREAM-SUB-003",
        section="3.1.6",
        title="SubscribeToTask rejects terminal tasks",
        level=RequirementLevel.MUST,
        description=(
            "SubscribeToTask MUST return UnsupportedOperationError when "
            "attempted on a task that is in a terminal state."
        ),
        operation=OperationType.SUBSCRIBE_TO_TASK,
        binding=SUBSCRIBE_TO_TASK_BINDING,
        proto_request_type="SubscribeToTaskRequest",
        expected_behavior="UnsupportedOperationError returned for terminal task",
        spec_url=f"{SPEC_BASE}316-subscribe-to-task",
        tags=[STREAMING, SUBSCRIBE, ERROR, MULTI_OPERATION],

    ),
    RequirementSpec(
        id="STREAM-SUB-004",
        section="3.1.6",
        title="SubscribeToTask returns TaskNotFoundError for invalid task",
        level=RequirementLevel.MUST,
        description=(
            "SubscribeToTask MUST return TaskNotFoundError when the task ID "
            "does not exist or is not accessible."
        ),
        operation=OperationType.SUBSCRIBE_TO_TASK,
        binding=SUBSCRIBE_TO_TASK_BINDING,
        proto_request_type="SubscribeToTaskRequest",
        expected_behavior="TaskNotFoundError returned",
        expected_error=TASK_NOT_FOUND_ERROR,
        spec_url=f"{SPEC_BASE}316-subscribe-to-task",
        tags=[STREAMING, SUBSCRIBE, ERROR],
        sample_input={"id": tck_id("nonexistent-sub-004")},
    ),
]
