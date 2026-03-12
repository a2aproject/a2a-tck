"""Core operation requirements from A2A specification Section 3.

Covers: SendMessage, SendStreamingMessage, GetTask, ListTasks, CancelTask,
SubscribeToTask, blocking semantics, error handling, capability validation,
multi-turn interactions (contextId/taskId).
"""

from __future__ import annotations

from tck.requirements.base import (
    CANCEL_TASK_BINDING,
    GET_TASK_BINDING,
    LIST_TASKS_BINDING,
    SEND_MESSAGE_BINDING,
    SEND_STREAMING_MESSAGE_BINDING,
    SPEC_BASE,
    TASK_NOT_FOUND_ERROR,
    OperationType,
    RequirementLevel,
    RequirementSpec,
    tck_id,
)
from tck.requirements.tags import (
    AGENT_CARD,
    AUTHORIZATION,
    CANCEL_TASK,
    CAPABILITY,
    CONTEXT,
    CORE,
    ERROR,
    EXECUTION_MODE,
    EXTENSION,
    GET_TASK,
    LIST_TASKS,
    MULTI_OPERATION,
    MULTI_TURN,
    PAGINATION,
    PUSH_NOTIFICATION,
    SEND_MESSAGE,
    STREAMING,
    TASK_ID,
    VALIDATION,
)
from tck.validators.payload import validate_message_response_contains_field


CORE_OPERATIONS_REQUIREMENTS: list[RequirementSpec] = [
    # --- SendMessage (Section 3.1.1) ---
    RequirementSpec(
        id="CORE-SEND-001",
        section="3.1.1",
        title="SendMessage returns Task or Message",
        level=RequirementLevel.MUST,
        description=(
            "The SendMessage operation MUST return immediately with either "
            "task information or a response message."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        proto_response_type="SendMessageResponse",
        expected_behavior=(
            "Response contains either a Task object or a Message object"
        ),
        spec_url=f"{SPEC_BASE}311-send-message",
        tags=[CORE, SEND_MESSAGE],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Hello from TCK"}],
                "messageId": tck_id("send-001"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-SEND-002",
        section="3.1.1",
        title="SendMessage rejects messages to terminal tasks",
        level=RequirementLevel.MUST,
        description=(
            "Messages sent to Tasks that are in a terminal state "
            "(completed, canceled, rejected) MUST return UnsupportedOperationError."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        expected_behavior="UnsupportedOperationError returned for terminal task",
        spec_url=f"{SPEC_BASE}311-send-message",
        tags=[CORE, SEND_MESSAGE, ERROR],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Message to terminal task"}],
                "messageId": tck_id("send-002"),
                "taskId": tck_id("terminal-send-002"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-SEND-003",
        section="3.1.1",
        title="SendMessage returns ContentTypeNotSupportedError for unsupported media",
        level=RequirementLevel.MUST,
        description=(
            "A Media Type provided in the request's message parts that is not "
            "supported by the agent MUST result in ContentTypeNotSupportedError."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        expected_behavior="ContentTypeNotSupportedError returned",
        spec_url=f"{SPEC_BASE}311-send-message",
        tags=[CORE, SEND_MESSAGE, ERROR],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [
                    {
                        "raw": "dGNr",
                        "mediaType": "application/x-unsupported-tck-type",
                    },
                ],
                "messageId": tck_id("send-003"),
            },
        },
    ),
    # --- SendStreamingMessage (Section 3.1.2) ---
    RequirementSpec(
        id="CORE-STREAM-001",
        section="3.1.2",
        title="SendStreamingMessage establishes streaming connection",
        level=RequirementLevel.MUST,
        description=(
            "The SendStreamingMessage operation MUST establish a streaming "
            "connection for real-time updates."
        ),
        operation=OperationType.SEND_STREAMING_MESSAGE,
        binding=SEND_STREAMING_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        proto_response_type="StreamResponse",
        expected_behavior="Streaming connection established with real-time events",
        spec_url=f"{SPEC_BASE}312-send-streaming-message",
        tags=[CORE, STREAMING],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Stream hello from TCK"}],
                "messageId": tck_id("stream-001"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-STREAM-002",
        section="3.1.2",
        title="Message-only stream contains exactly one Message then closes",
        level=RequirementLevel.MUST,
        description=(
            "If the agent returns a Message, the stream MUST contain exactly "
            "one Message object and then close immediately."
        ),
        operation=OperationType.SEND_STREAMING_MESSAGE,
        binding=SEND_STREAMING_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        proto_response_type="StreamResponse",
        expected_behavior="Stream contains single Message then closes",
        spec_url=f"{SPEC_BASE}312-send-streaming-message",
        tags=[CORE, STREAMING],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Stream message-only response"}],
                "messageId": tck_id("stream-002"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-STREAM-003",
        section="3.1.2",
        title="Task lifecycle stream begins with Task and closes at terminal state",
        level=RequirementLevel.MUST,
        description=(
            "If the agent returns a Task, the stream MUST begin with the Task "
            "object, followed by zero or more update events. The stream MUST "
            "close when the task reaches a terminal state."
        ),
        operation=OperationType.SEND_STREAMING_MESSAGE,
        binding=SEND_STREAMING_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        proto_response_type="StreamResponse",
        expected_behavior=(
            "Stream starts with Task, followed by events, closes at terminal state"
        ),
        spec_url=f"{SPEC_BASE}312-send-streaming-message",
        tags=[CORE, STREAMING],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Stream task lifecycle"}],
                "messageId": tck_id("stream-003"),
            },
        },
    ),
    # --- GetTask (Section 3.1.3) ---
    RequirementSpec(
        id="CORE-GET-001",
        section="3.1.3",
        title="GetTask returns current task state",
        level=RequirementLevel.MUST,
        description=(
            "GetTask retrieves the current state of a previously initiated task "
            "including status, artifacts, and optionally history."
        ),
        operation=OperationType.GET_TASK,
        binding=GET_TASK_BINDING,
        proto_request_type="GetTaskRequest",
        proto_response_type="Task",
        expected_behavior="Current task state returned with status and artifacts",
        spec_url=f"{SPEC_BASE}313-get-task",
        tags=[CORE, GET_TASK, MULTI_OPERATION],
        sample_input={"id": tck_id("existing-get-001")},
    ),
    RequirementSpec(
        id="CORE-GET-002",
        section="3.1.3",
        title="GetTask returns TaskNotFoundError for invalid task ID",
        level=RequirementLevel.MUST,
        description=(
            "GetTask MUST return TaskNotFoundError when the task ID does not "
            "exist or is not accessible."
        ),
        operation=OperationType.GET_TASK,
        binding=GET_TASK_BINDING,
        proto_request_type="GetTaskRequest",
        expected_behavior="TaskNotFoundError returned",
        expected_error=TASK_NOT_FOUND_ERROR,
        spec_url=f"{SPEC_BASE}313-get-task",
        tags=[CORE, GET_TASK, ERROR],
        sample_input={"id": tck_id("nonexistent-get-002")},
    ),
    # --- ListTasks (Section 3.1.4) ---
    RequirementSpec(
        id="CORE-LIST-001",
        section="3.1.4",
        title="ListTasks returns only authorized tasks",
        level=RequirementLevel.MUST,
        description=(
            "The ListTasks operation MUST return only tasks visible to the "
            "authenticated client."
        ),
        operation=OperationType.LIST_TASKS,
        binding=LIST_TASKS_BINDING,
        proto_request_type="ListTasksRequest",
        proto_response_type="ListTasksResponse",
        expected_behavior="Only authorized tasks returned",
        spec_url=f"{SPEC_BASE}314-list-tasks",
        tags=[CORE, LIST_TASKS, AUTHORIZATION],
        sample_input={"context_id": tck_id("test-context")},
    ),
    RequirementSpec(
        id="CORE-LIST-002",
        section="3.1.4",
        title="ListTasks uses cursor-based pagination",
        level=RequirementLevel.MUST,
        description=(
            "ListTasks MUST use cursor-based pagination via "
            "pageToken/nextPageToken."
        ),
        operation=OperationType.LIST_TASKS,
        binding=LIST_TASKS_BINDING,
        proto_request_type="ListTasksRequest",
        proto_response_type="ListTasksResponse",
        expected_behavior="Cursor-based pagination with pageToken/nextPageToken",
        spec_url=f"{SPEC_BASE}314-list-tasks",
        tags=[CORE, LIST_TASKS, PAGINATION],
        sample_input={"context_id": tck_id("test-context"), "page_size": 2},
    ),
    RequirementSpec(
        id="CORE-LIST-003",
        section="3.1.4",
        title="ListTasks sorts by status timestamp descending",
        level=RequirementLevel.MUST,
        description=(
            "Implementations MUST return tasks sorted by their status timestamp "
            "in descending order (most recently updated first)."
        ),
        operation=OperationType.LIST_TASKS,
        binding=LIST_TASKS_BINDING,
        proto_request_type="ListTasksRequest",
        proto_response_type="ListTasksResponse",
        expected_behavior="Tasks sorted by status timestamp descending",
        spec_url=f"{SPEC_BASE}314-list-tasks",
        tags=[CORE, LIST_TASKS],
        sample_input={"context_id": tck_id("test-context")},
    ),
    RequirementSpec(
        id="CORE-LIST-004",
        section="3.1.4",
        title="ListTasks nextPageToken empty string on final page",
        level=RequirementLevel.MUST,
        description=(
            "The nextPageToken field MUST always be present in the response. "
            "When there are no more results, it MUST be set to an empty string."
        ),
        operation=OperationType.LIST_TASKS,
        binding=LIST_TASKS_BINDING,
        proto_request_type="ListTasksRequest",
        proto_response_type="ListTasksResponse",
        expected_behavior="nextPageToken is empty string on final page",
        spec_url=f"{SPEC_BASE}314-list-tasks",
        tags=[CORE, LIST_TASKS, PAGINATION],
        sample_input={"context_id": tck_id("test-context"), "page_size": 100},
    ),
    RequirementSpec(
        id="CORE-LIST-005",
        section="3.1.4",
        title="ListTasks omits artifacts when includeArtifacts is false",
        level=RequirementLevel.MUST,
        description=(
            "When includeArtifacts is false (the default), the artifacts field "
            "MUST be omitted entirely from each Task object in the response."
        ),
        operation=OperationType.LIST_TASKS,
        binding=LIST_TASKS_BINDING,
        proto_request_type="ListTasksRequest",
        proto_response_type="ListTasksResponse",
        expected_behavior="Artifacts field omitted entirely when includeArtifacts=false",
        spec_url=f"{SPEC_BASE}314-list-tasks",
        tags=[CORE, LIST_TASKS],
        sample_input={"context_id": tck_id("test-context"), "include_artifacts": False},
    ),
    # --- CancelTask (Section 3.1.5) ---
    RequirementSpec(
        id="CORE-CANCEL-001",
        section="3.1.5",
        title="CancelTask returns updated task with cancellation status",
        level=RequirementLevel.MUST,
        description=(
            "The CancelTask operation attempts to cancel the specified task "
            "and returns its updated state."
        ),
        operation=OperationType.CANCEL_TASK,
        binding=CANCEL_TASK_BINDING,
        proto_request_type="CancelTaskRequest",
        proto_response_type="Task",
        expected_behavior="Updated Task with cancellation status returned",
        spec_url=f"{SPEC_BASE}315-cancel-task",
        tags=[CORE, CANCEL_TASK, MULTI_OPERATION],
        sample_input={"id": tck_id("cancelable-cancel-001")},
    ),
    RequirementSpec(
        id="CORE-CANCEL-002",
        section="3.1.5",
        title="CancelTask returns TaskNotCancelableError for terminal tasks",
        level=RequirementLevel.MUST,
        description=(
            "CancelTask MUST return TaskNotCancelableError when the task is "
            "not in a cancelable state (already completed, failed, or canceled)."
        ),
        operation=OperationType.CANCEL_TASK,
        binding=CANCEL_TASK_BINDING,
        proto_request_type="CancelTaskRequest",
        expected_behavior="TaskNotCancelableError returned",
        spec_url=f"{SPEC_BASE}315-cancel-task",
        tags=[CORE, CANCEL_TASK, ERROR, MULTI_OPERATION],
        sample_input={"id": tck_id("terminal-cancel-002")},
    ),
    RequirementSpec(
        id="CORE-CANCEL-003",
        section="3.1.5",
        title="CancelTask returns TaskNotFoundError for invalid task ID",
        level=RequirementLevel.MUST,
        description=(
            "CancelTask MUST return TaskNotFoundError when the task ID does "
            "not exist or is not accessible."
        ),
        operation=OperationType.CANCEL_TASK,
        binding=CANCEL_TASK_BINDING,
        proto_request_type="CancelTaskRequest",
        expected_behavior="TaskNotFoundError returned",
        expected_error=TASK_NOT_FOUND_ERROR,
        spec_url=f"{SPEC_BASE}315-cancel-task",
        tags=[CORE, CANCEL_TASK, ERROR],
        sample_input={"id": tck_id("nonexistent-cancel-003")},
    ),
    # --- Execution Mode (Section 3.2.2) ---
    RequirementSpec(
        id="CORE-EXECUTION-MODE-001",
        section="3.2.2",
        title="Blocking mode waits for terminal or interrupted state",
        level=RequirementLevel.MUST,
        description=(
            "When return_immediately is false or unset, the operation MUST wait "
            "until the task reaches a terminal state (completed, failed, canceled, "
            "rejected) or an interrupted state (input_required, auth_required) "
            "before returning. This is the default behavior."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        proto_response_type="SendMessageResponse",
        expected_behavior="Response delayed until terminal or interrupted state",
        spec_url=f"{SPEC_BASE}322-sendmessageconfiguration",
        tags=[CORE, EXECUTION_MODE],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Blocking request"}],
                "messageId": tck_id("block-001"),
            },
            "configuration": {"returnImmediately": False},
        },
    ),
    RequirementSpec(
        id="CORE-EXECUTION-MODE-002",
        section="3.2.2",
        title="Non-blocking mode returns immediately",
        level=RequirementLevel.MUST,
        description=(
            "When return_immediately is true, the operation MUST return immediately "
            "after creating the task, even if processing is still in progress."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        proto_request_type="SendMessageRequest",
        proto_response_type="SendMessageResponse",
        expected_behavior="Response returned immediately with in-progress state",
        spec_url=f"{SPEC_BASE}322-sendmessageconfiguration",
        tags=[CORE, EXECUTION_MODE],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Non-blocking request"}],
                "messageId": tck_id("block-002"),
            },
            "configuration": {"returnImmediately": True},
        },
    ),
    # --- Error Handling (Section 3.3.2) ---
    RequirementSpec(
        id="CORE-ERR-001",
        section="3.3.2",
        title="Server returns appropriate errors with actionable information",
        level=RequirementLevel.MUST,
        description=(
            "Servers MUST return appropriate errors and SHOULD provide "
            "actionable information to help clients resolve issues."
        ),
        expected_behavior="Error responses include code, message, and optional details",
        spec_url=f"{SPEC_BASE}332-error-handling",
        tags=[CORE, ERROR],
    ),
    RequirementSpec(
        id="CORE-ERR-002",
        section="3.3.2",
        title="Server validates all input parameters before processing",
        level=RequirementLevel.MUST,
        description=(
            "Servers MUST validate all input parameters before processing."
        ),
        expected_behavior="Invalid parameters rejected with validation error",
        spec_url=f"{SPEC_BASE}332-error-handling",
        tags=[CORE, ERROR, VALIDATION],
    ),
    # --- Capability Validation (Section 3.3.4) ---
    RequirementSpec(
        id="CORE-CAP-001",
        section="3.3.4",
        title="Push notification operations return error when not supported",
        level=RequirementLevel.MUST,
        description=(
            "If AgentCard.capabilities.pushNotifications is false or not present, "
            "push notification operations MUST return "
            "PushNotificationNotSupportedError."
        ),
        expected_behavior="PushNotificationNotSupportedError returned",
        spec_url=f"{SPEC_BASE}334-capability-validation",
        tags=[CORE, CAPABILITY, PUSH_NOTIFICATION],
    ),
    RequirementSpec(
        id="CORE-CAP-002",
        section="3.3.4",
        title="Streaming operations return error when not supported",
        level=RequirementLevel.MUST,
        description=(
            "If AgentCard.capabilities.streaming is false or not present, "
            "SendStreamingMessage and SubscribeToTask MUST return "
            "UnsupportedOperationError."
        ),
        expected_behavior="UnsupportedOperationError returned",
        spec_url=f"{SPEC_BASE}334-capability-validation",
        tags=[CORE, CAPABILITY, STREAMING],
    ),
    RequirementSpec(
        id="CORE-CAP-003",
        section="3.3.4",
        title="Extended agent card operations return error when not supported",
        level=RequirementLevel.MUST,
        description=(
            "If AgentCard.capabilities.extendedAgentCard is false or not present, "
            "GetExtendedAgentCard MUST return UnsupportedOperationError."
        ),
        expected_behavior="UnsupportedOperationError returned",
        spec_url=f"{SPEC_BASE}334-capability-validation",
        tags=[CORE, CAPABILITY, AGENT_CARD],
    ),
    RequirementSpec(
        id="CORE-CAP-004",
        section="3.3.4",
        title="Required extension missing returns ExtensionSupportRequiredError",
        level=RequirementLevel.MUST,
        description=(
            "When a client requests use of an extension marked as required=true "
            "but the client does not declare support, the agent MUST return "
            "ExtensionSupportRequiredError."
        ),
        expected_behavior="ExtensionSupportRequiredError returned",
        spec_url=f"{SPEC_BASE}334-capability-validation",
        tags=[CORE, CAPABILITY, EXTENSION],
    ),
    # --- Multi-Turn Interactions (Section 3.4) ---
    RequirementSpec(
        id="CORE-MULTI-001",
        section="3.4.1",
        title="Agent may generate contextId when not provided",
        level=RequirementLevel.MAY,
        description=(
            "Agents MAY generate a new contextId when processing a Message "
            "that does not include a contextId field."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="Response may contain server-generated contextId",
        spec_url=f"{SPEC_BASE}341-context-identifier-semantics",
        tags=[CORE, MULTI_TURN, CONTEXT],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Message without contextId"}],
                "messageId": tck_id("multi-001"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-MULTI-001a",
        section="3.4.1",
        title="Generated contextId must be included in response",
        level=RequirementLevel.MUST,
        description=(
            "If an agent generates a new contextId, it MUST be included in "
            "the response (either Task or Message)."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="Generated contextId present in response",
        spec_url=f"{SPEC_BASE}341-context-identifier-semantics",
        tags=[CORE, MULTI_TURN, CONTEXT],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Message without contextId"}],
                "messageId": tck_id("multi-001a"),
            },
        },
        validators=[validate_message_response_contains_field("contextId")],
    ),
    RequirementSpec(
        id="CORE-MULTI-002",
        section="3.4.1",
        title="Agent may accept client-provided contextId",
        level=RequirementLevel.MAY,
        description=(
            "Agents MAY accept and preserve client-provided contextId values."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="Response contextId matches client-provided value",
        spec_url=f"{SPEC_BASE}341-context-identifier-semantics",
        tags=[CORE, MULTI_TURN, CONTEXT],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Message with contextId"}],
                "messageId": tck_id("multi-002"),
                "contextId": tck_id("client-context-001"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-MULTI-002a",
        section="3.4.1",
        title="Agent rejects unacceptable client-provided contextId",
        level=RequirementLevel.MUST,
        description=(
            "If an agent cannot accept a client-provided contextId, it MUST "
            "reject the request with an error and MUST NOT generate a new "
            "contextId for the response."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="Error returned when client contextId not accepted",
        spec_url=f"{SPEC_BASE}341-context-identifier-semantics",
        tags=[CORE, MULTI_TURN, CONTEXT, ERROR],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Message with client contextId"}],
                "messageId": tck_id("multi-002a"),
                "contextId": tck_id("client-context-rejected"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-MULTI-003",
        section="3.4.2",
        title="Agent generates unique taskId for new tasks",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST generate a unique taskId for each new task they create. "
            "The generated taskId MUST be included in the Task object."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="Task contains server-generated unique taskId",
        spec_url=f"{SPEC_BASE}342-task-identifier-semantics",
        tags=[CORE, MULTI_TURN, TASK_ID],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "New task request"}],
                "messageId": tck_id("multi-003"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-MULTI-004",
        section="3.4.2",
        title="Agent returns TaskNotFoundError for invalid taskId in message",
        level=RequirementLevel.MUST,
        description=(
            "When a client includes a taskId in a Message that does not "
            "correspond to an existing task, agents MUST return TaskNotFoundError."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="TaskNotFoundError returned",
        spec_url=f"{SPEC_BASE}342-task-identifier-semantics",
        tags=[CORE, MULTI_TURN, TASK_ID, ERROR],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Message to invalid task"}],
                "messageId": tck_id("multi-004"),
                "taskId": tck_id("nonexistent-multi-004"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-MULTI-005",
        section="3.4.3",
        title="Agent infers contextId from task when only taskId provided",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST infer contextId from the task if only taskId is provided."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="contextId inferred from referenced task",
        spec_url=f"{SPEC_BASE}343-multi-turn-conversation-patterns",
        tags=[CORE, MULTI_TURN, MULTI_OPERATION],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Follow-up with taskId only"}],
                "messageId": tck_id("multi-005"),
                "taskId": tck_id("existing-multi-005"),
            },
        },
    ),
    RequirementSpec(
        id="CORE-MULTI-006",
        section="3.4.3",
        title="Agent rejects mismatching contextId and taskId",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST reject messages containing mismatching contextId and "
            "taskId (i.e., the provided contextId is different from that of "
            "the referenced Task)."
        ),
        operation=OperationType.SEND_MESSAGE,
        binding=SEND_MESSAGE_BINDING,
        expected_behavior="Error returned for mismatching contextId/taskId",
        spec_url=f"{SPEC_BASE}343-multi-turn-conversation-patterns",
        tags=[CORE, MULTI_TURN, ERROR, MULTI_OPERATION],
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Mismatched context"}],
                "messageId": tck_id("multi-006"),
                "taskId": tck_id("existing-multi-006"),
                "contextId": tck_id("wrong-context"),
            },
        },
    ),
]
