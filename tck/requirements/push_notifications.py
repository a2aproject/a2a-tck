"""Push notification requirements from A2A specification Sections 3.1.7-10, 4.3.

Covers: CRUD operations for push notification configs, idempotent delete,
webhook delivery, authentication in webhook requests.
"""

from tck.requirements.base import (
    CREATE_PUSH_CONFIG_BINDING,
    DELETE_PUSH_CONFIG_BINDING,
    GET_PUSH_CONFIG_BINDING,
    LIST_PUSH_CONFIGS_BINDING,
    SPEC_BASE,
    OperationType,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    AUTH,
    CREATE,
    DELETE,
    DELIVERY,
    ERROR,
    FORMAT,
    GET,
    IDEMPOTENT,
    LIST,
    PUSH_NOTIFICATION,
)


PUSH_NOTIFICATION_REQUIREMENTS: list[RequirementSpec] = [
    # --- Create Push Notification Config (Section 3.1.7) ---
    RequirementSpec(
        id="PUSH-CREATE-001",
        section="3.1.7",
        title="CreatePushNotificationConfig establishes webhook endpoint",
        level=RequirementLevel.MUST,
        description=(
            "The CreatePushNotificationConfig operation MUST establish a "
            "webhook endpoint for task update notifications."
        ),
        operation=OperationType.CREATE_PUSH_CONFIG,
        binding=CREATE_PUSH_CONFIG_BINDING,
        proto_request_type="CreateTaskPushNotificationConfigRequest",
        proto_response_type="PushNotificationConfig",
        expected_behavior="Webhook endpoint created and config returned with ID",
        spec_url=f"{SPEC_BASE}317-create-push-notification-config",
        tags=[PUSH_NOTIFICATION, CREATE],
        sample_input={
            "task_id": "tck-existing-task",
            "config_id": "tck-push-cfg-001",
            "config": {
                "url": "https://example.com/tck/notifications",
                "authentication": {
                    "scheme": "Bearer",
                    "credentials": "tck-test-token",
                },
            },
        },
    ),
    RequirementSpec(
        id="PUSH-CREATE-002",
        section="3.1.7",
        title="Push config persists until task completion or deletion",
        level=RequirementLevel.MUST,
        description=(
            "The push notification configuration MUST persist until task "
            "completion or explicit deletion."
        ),
        operation=OperationType.CREATE_PUSH_CONFIG,
        binding=CREATE_PUSH_CONFIG_BINDING,
        expected_behavior="Config persists across multiple task updates",
        spec_url=f"{SPEC_BASE}317-create-push-notification-config",
        tags=[PUSH_NOTIFICATION, CREATE],
        sample_input={
            "task_id": "tck-existing-task",
            "config_id": "tck-push-cfg-002",
            "config": {
                "url": "https://example.com/tck/notifications/persist",
                "authentication": {
                    "scheme": "Bearer",
                    "credentials": "tck-test-token",
                },
            },
        },
    ),
    # --- Get Push Notification Config (Section 3.1.8) ---
    RequirementSpec(
        id="PUSH-GET-001",
        section="3.1.8",
        title="GetPushNotificationConfig returns configuration details",
        level=RequirementLevel.MUST,
        description=(
            "The GetPushNotificationConfig operation MUST return configuration "
            "details including webhook URL and notification settings."
        ),
        operation=OperationType.GET_PUSH_CONFIG,
        binding=GET_PUSH_CONFIG_BINDING,
        proto_request_type="GetTaskPushNotificationConfigRequest",
        proto_response_type="PushNotificationConfig",
        expected_behavior="Full configuration details returned",
        spec_url=f"{SPEC_BASE}318-get-push-notification-config",
        tags=[PUSH_NOTIFICATION, GET],
        sample_input={"task_id": "tck-existing-task", "id": "tck-push-cfg-001"},
    ),
    RequirementSpec(
        id="PUSH-GET-002",
        section="3.1.8",
        title="GetPushNotificationConfig fails for nonexistent config",
        level=RequirementLevel.MUST,
        description=(
            "The GetPushNotificationConfig operation MUST fail if the "
            "configuration does not exist or the client lacks access."
        ),
        operation=OperationType.GET_PUSH_CONFIG,
        binding=GET_PUSH_CONFIG_BINDING,
        proto_request_type="GetTaskPushNotificationConfigRequest",
        expected_behavior="Error returned for nonexistent config",
        spec_url=f"{SPEC_BASE}318-get-push-notification-config",
        tags=[PUSH_NOTIFICATION, GET, ERROR],
        sample_input={
            "task_id": "tck-existing-task",
            "id": "tck-nonexistent-push-cfg",
        },
    ),
    # --- List Push Notification Configs (Section 3.1.9) ---
    RequirementSpec(
        id="PUSH-LIST-001",
        section="3.1.9",
        title="ListPushNotificationConfigs returns all active configs",
        level=RequirementLevel.MUST,
        description=(
            "The ListPushNotificationConfig operation MUST return all active "
            "push notification configurations for the specified task."
        ),
        operation=OperationType.LIST_PUSH_CONFIGS,
        binding=LIST_PUSH_CONFIGS_BINDING,
        proto_request_type="ListTaskPushNotificationConfigRequest",
        proto_response_type="ListTaskPushNotificationConfigResponse",
        expected_behavior="All active configs returned for task",
        spec_url=f"{SPEC_BASE}319-list-push-notification-configs",
        tags=[PUSH_NOTIFICATION, LIST],
        sample_input={"task_id": "tck-existing-task"},
    ),
    # --- Delete Push Notification Config (Section 3.1.10) ---
    RequirementSpec(
        id="PUSH-DEL-001",
        section="3.1.10",
        title="DeletePushNotificationConfig permanently removes config",
        level=RequirementLevel.MUST,
        description=(
            "The DeletePushNotificationConfig operation MUST permanently "
            "remove the specified push notification configuration."
        ),
        operation=OperationType.DELETE_PUSH_CONFIG,
        binding=DELETE_PUSH_CONFIG_BINDING,
        proto_request_type="DeleteTaskPushNotificationConfigRequest",
        expected_behavior="Config permanently removed, no further notifications",
        spec_url=f"{SPEC_BASE}3110-delete-push-notification-config",
        tags=[PUSH_NOTIFICATION, DELETE],
        sample_input={"task_id": "tck-existing-task", "id": "tck-push-cfg-001"},
    ),
    RequirementSpec(
        id="PUSH-DEL-002",
        section="3.1.10",
        title="DeletePushNotificationConfig is idempotent",
        level=RequirementLevel.MUST,
        description=(
            "The DeletePushNotificationConfig operation MUST be idempotent - "
            "multiple deletions of the same config have the same effect."
        ),
        operation=OperationType.DELETE_PUSH_CONFIG,
        binding=DELETE_PUSH_CONFIG_BINDING,
        proto_request_type="DeleteTaskPushNotificationConfigRequest",
        expected_behavior="Repeated deletions succeed without error",
        spec_url=f"{SPEC_BASE}3110-delete-push-notification-config",
        tags=[PUSH_NOTIFICATION, DELETE, IDEMPOTENT],
        sample_input={
            "task_id": "tck-existing-task",
            "id": "tck-push-cfg-idempotent",
        },
    ),
    # --- Webhook Delivery (Section 4.3.3) ---
    RequirementSpec(
        id="PUSH-DELIVER-001",
        section="4.3.3",
        title="Agent includes authentication in webhook requests",
        level=RequirementLevel.MUST,
        description=(
            "The agent MUST include authentication credentials in the webhook "
            "request headers as specified in the PushNotificationConfig."
            "authentication field."
        ),
        expected_behavior="Webhook requests include configured auth credentials",
        spec_url=f"{SPEC_BASE}433-push-notification-payload",
        tags=[PUSH_NOTIFICATION, DELIVERY, AUTH],
    ),
    RequirementSpec(
        id="PUSH-DELIVER-002",
        section="4.3.3",
        title="Agent attempts delivery at least once per webhook",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST attempt delivery at least once for each configured "
            "webhook."
        ),
        expected_behavior="At-least-once delivery attempted",
        spec_url=f"{SPEC_BASE}433-push-notification-payload",
        tags=[PUSH_NOTIFICATION, DELIVERY],
    ),
    RequirementSpec(
        id="PUSH-DELIVER-003",
        section="4.3.3",
        title="Webhook payload uses StreamResponse format",
        level=RequirementLevel.MUST,
        description=(
            "The webhook payload MUST use the StreamResponse format containing "
            "exactly one of: task, message, statusUpdate, or artifactUpdate."
        ),
        expected_behavior="Payload is valid StreamResponse with single field",
        spec_url=f"{SPEC_BASE}433-push-notification-payload",
        tags=[PUSH_NOTIFICATION, DELIVERY, FORMAT],
    ),
]
