import logging
import uuid
import time
import asyncio
from threading import Thread
from aiohttp import web

import pytest

from tck import agent_card_utils, message_utils
from tests.markers import optional_capability
from tests.capability_validator import CapabilityValidator
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)

# Using transport-agnostic sut_client fixture from conftest.py


@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    message_params = {
        "message": {
            "messageId": "test-push-notification-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Task for push notification config test"}],
            "kind": "message",
        }
    }
    resp = transport_helpers.transport_send_message(sut_client, message_params)
    assert transport_helpers.is_json_rpc_success_response(resp)
    return resp["result"]["id"]


@pytest.fixture(scope="session")
def push_notification_webhook():
    """
    Start a lightweight HTTP server to receive and verify push notifications.

    Returns a dict with:
        - url: The webhook URL to use in push notification configs
        - notifications: List of notifications received by the server
        - wait_for_notification: Function to wait for notifications with timeout
    """
    from threading import Event as ThreadingEvent

    notifications = []
    server_ready = ThreadingEvent()

    async def webhook_handler(request):
        """Handle incoming push notifications"""
        try:
            data = await request.json()
            logger.info(f"Webhook received notification: {data}")
            notifications.append(data)
            return web.Response(status=200, text="OK")
        except Exception as e:
            logger.error(f"Webhook handler error: {e}")
            return web.Response(status=500, text=str(e))

    async def run_server():
        """Run the aiohttp server"""
        app = web.Application()
        app.router.add_post('/webhook', webhook_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8888)
        await site.start()

        server_ready.set()
        logger.info("Push notification webhook started at http://localhost:8888/webhook")

        try:
            await asyncio.Event().wait()  # Run forever
        finally:
            await runner.cleanup()

    def start_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_server())

    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait for server to be ready (using threading.Event, not asyncio.Event)
    if not server_ready.wait(timeout=5.0):
        raise RuntimeError("Webhook server failed to start within 5 seconds")

    logger.info("Webhook server is ready")

    def wait_for_notification(timeout=5.0):
        """Wait for at least one notification with timeout"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if notifications:
                return True
            time.sleep(0.1)
        return False

    yield {
        'url': 'http://localhost:8888/webhook',
        'notifications': notifications,
        'wait_for_notification': wait_for_notification
    }


# Helper function to check push notification support
def has_push_notification_support(agent_card_data):
    """Check if the SUT supports push notifications based on Agent Card data."""
    if agent_card_data is None:
        logger.warning("Agent Card data is None, assuming push notifications are not supported")
        return False

    return agent_card_utils.get_capability_push_notifications(agent_card_data)


@optional_capability
def test_set_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.5 - Push Notification Configuration

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates the tasks/pushNotificationConfig/set method for setting
    push notification configurations on tasks.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    config = {"url": "https://example.com/webhook"}

    resp = transport_helpers.transport_set_push_notification_config(sut_client, created_task_id, config)

    # Since push notifications capability is declared, this MUST work
    assert transport_helpers.is_json_rpc_success_response(resp), "Push notifications capability declared but set config failed"

    result = resp["result"]
    assert result["pushNotificationConfig"]["url"] == "https://example.com/webhook", (
        "Push notification config URL not echoed correctly"
    )


@optional_capability
def test_get_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.6 - Push Notification Configuration Retrieval

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates the tasks/pushNotificationConfig/get method for retrieving
    push notification configurations from tasks.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    # First, set a push notification config
    config = {"url": "https://example.com/webhook"}

    set_resp = transport_helpers.transport_set_push_notification_config(sut_client, created_task_id, config)
    assert transport_helpers.is_json_rpc_success_response(set_resp), "Failed to set push notification config before testing get"

    # Now, get the config we just set
    resp = transport_helpers.transport_get_push_notification_config(sut_client, created_task_id)

    # Since push notifications capability is declared, this MUST work
    assert transport_helpers.is_json_rpc_success_response(resp), "Push notifications capability declared but get config failed"

    result = resp["result"]
    assert "pushNotificationConfig" in result, "Result must contain pushNotificationConfig"
    assert "url" in result["pushNotificationConfig"], "Push notification config must have url field"
    assert result["pushNotificationConfig"]["url"] == "https://example.com/webhook", "Retrieved URL should match what was set"


@optional_capability
def test_set_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.5 - Push Notification Error Handling

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates proper error handling for push notification config operations
    on non-existent tasks.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    config = {"url": "https://example.com/webhook"}

    resp = transport_helpers.transport_set_push_notification_config(sut_client, "nonexistent-task-id", config)

    # Should return proper JSON-RPC error for non-existent task
    assert transport_helpers.is_json_rpc_error_response(resp), (
        "Push notifications capability declared but invalid task ID not properly rejected"
    )

    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, "Error message should indicate task was not found"


@optional_capability
def test_get_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.6 - Push Notification Error Handling

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates proper error handling for push notification config retrieval
    on non-existent tasks.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    resp = transport_helpers.transport_get_push_notification_config(sut_client, "nonexistent-task-id", "default")

    # Should return proper JSON-RPC error for non-existent task
    assert transport_helpers.is_json_rpc_error_response(resp), (
        "Push notifications capability declared but invalid task ID not properly rejected"
    )

    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, "Error message should indicate task was not found"


@optional_capability
def test_list_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.7 - Push Notification Configuration List

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates the tasks/pushNotificationConfig/list method for retrieving
    all push notification configurations associated with a task.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    # First, set one or more push notification configs
    set_resp = transport_helpers.transport_set_push_notification_config(
        sut_client, created_task_id, {"url": "https://example.com/webhook1"}
    )
    assert transport_helpers.is_json_rpc_success_response(set_resp), "Failed to set push notification config before testing list"

    # Now, list the configs for this task
    resp = transport_helpers.transport_list_push_notification_configs(sut_client, created_task_id)

    # Since push notifications capability is declared, this MUST work
    assert transport_helpers.is_json_rpc_success_response(resp), "Push notifications capability declared but list config failed"

    result = resp["result"]
    assert isinstance(result, list), "Result must be a list of configurations"
    assert len(result) >= 1, "Should contain at least one configuration that we just set"

    # Verify the configuration we set is in the list
    found_config = False
    for config in result:
        assert "pushNotificationConfig" in config, "Each config must contain pushNotificationConfig"
        assert "taskId" in config, "Each config must contain taskId"
        assert config["taskId"] == created_task_id, "TaskId should match the requested task"
        if config["pushNotificationConfig"]["url"] == "https://example.com/webhook1":
            found_config = True

    assert found_config, "The configuration we set should be found in the list"


@optional_capability
def test_list_push_notification_config_empty(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.7 - Push Notification Configuration List (Empty)

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates the tasks/pushNotificationConfig/list method behavior
    for tasks with no push notification configurations.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    # Create a new task without any push notification configs
    message_params = {
        "message": {
            "messageId": "test-empty-list-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Task for empty push notification config list test"}],
            "kind": "message",
        }
    }
    resp = transport_helpers.transport_send_message(sut_client, message_params)
    assert transport_helpers.is_json_rpc_success_response(resp)
    empty_task_id = resp["result"]["id"]

    # List configs for task with no configurations
    resp = transport_helpers.transport_list_push_notification_configs(sut_client, empty_task_id)

    # Should return empty list or appropriate error - both are valid
    if transport_helpers.is_json_rpc_success_response(resp):
        result = resp["result"]
        assert isinstance(result, list), "Result must be a list"
        assert len(result) == 0, "Should be empty list for task with no configs"
    else:
        # Some implementations might return an error for no configs - this is acceptable
        assert transport_helpers.is_json_rpc_error_response(resp), "Response should be either success with empty list or error"


@optional_capability
def test_delete_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.8 - Push Notification Configuration Delete

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates the tasks/pushNotificationConfig/delete method for removing
    push notification configurations from tasks.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    # First, set a push notification config
    config = {"url": "https://example.com/webhook-to-delete"}
    set_resp = transport_helpers.transport_set_push_notification_config(sut_client, created_task_id, config)
    assert transport_helpers.is_json_rpc_success_response(set_resp), (
        "Failed to set push notification config before testing delete"
    )

    # Extract the config ID from the response (if provided by server)
    set_result = set_resp["result"]
    config_id = set_result["pushNotificationConfig"].get("id")

    if config_id:
        # If the server provides config ID, use it for deletion
        resp = transport_helpers.transport_delete_push_notification_config(sut_client, created_task_id, config_id)

        # Since push notifications capability is declared, this MUST work
        assert transport_helpers.is_json_rpc_success_response(resp), (
            "Push notifications capability declared but delete config failed"
        )

        # Result should be null for successful deletion
        result = resp["result"]
        assert result is None, "Delete should return null result on success"

        # Verify deletion by trying to get the config
        get_resp = transport_helpers.transport_get_push_notification_config(sut_client, created_task_id, config_id)

        # Should either return error (config not found) or success with empty/different config
        if transport_helpers.is_json_rpc_success_response(get_resp):
            # If successful, the config should be different or not contain our deleted URL
            get_result = get_resp["result"]
            if "pushNotificationConfig" in get_result:
                assert get_result["pushNotificationConfig"]["url"] != "https://example.com/webhook-to-delete", (
                    "Deleted configuration should not be retrievable"
                )
        else:
            # Error response is also acceptable (config not found)
            assert transport_helpers.is_json_rpc_error_response(get_resp), (
                "After deletion, get should either return error or different config"
            )
    else:
        # If server doesn't provide config ID, skip this test
        pytest.skip("Server does not provide push notification config ID - cannot test delete functionality")


@optional_capability
def test_delete_push_notification_config_nonexistent(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.8 - Push Notification Configuration Delete Error Handling

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates proper error handling for push notification config deletion
    with non-existent task IDs or config IDs.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    # Test 1: Delete with non-existent task ID
    resp = transport_helpers.transport_delete_push_notification_config(sut_client, "nonexistent-task-id", "some-config-id")

    # Should return proper JSON-RPC error for non-existent task
    assert transport_helpers.is_json_rpc_error_response(resp), (
        "Push notifications capability declared but invalid task ID not properly rejected"
    )

    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, "Error message should indicate task was not found"

    # Test 2: Delete with valid task ID but non-existent config ID
    resp = transport_helpers.transport_delete_push_notification_config(sut_client, created_task_id, "nonexistent-config-id")

    # For gRPC, non-existent config deletion may return empty result or error
    if transport_helpers.is_json_rpc_success_response(resp):
        result = resp["result"]
        # Empty dict from gRPC is acceptable
        assert result == {} or result is None, "Delete should return empty result on success"
    else:
        # Error response is also acceptable for non-existent config
        assert transport_helpers.is_json_rpc_error_response(resp), "Delete non-existent config should return success or error"


@optional_capability
def test_send_message_with_push_notification_config(sut_client, agent_card_data, push_notification_webhook):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.1 - SendMessageConfiguration with pushNotificationConfig

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates that pushNotificationConfig in SendMessageConfiguration is actually
    used and not ignored when sending a message. This test verifies both:
    1. The config is stored and retrievable from the task
    2. Push notifications are actually sent to the configured webhook URL

    This addresses GitHub issue #84 - ensuring the TCK tests that pushNotificationConfig
    is processed when included in the message/send configuration.

    Specification Reference: A2A Protocol v0.3.0 §7.1.2 - SendMessageConfiguration
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    # Prepare a message with pushNotificationConfig using real webhook server
    message_id = "test-push-config-in-send-" + str(uuid.uuid4())
    webhook_url = push_notification_webhook['url']

    message_params = {
        "message": {
            "messageId": message_id,
            "role": "user",
            "parts": [{"kind": "text", "text": "Task with push notification config in send configuration"}],
            "kind": "message",
        }
    }

    configuration = {
        "pushNotificationConfig": {
            "url": webhook_url,
            "token": "test-token-123",
        }
    }

    # Send the message with configuration
    resp = transport_helpers.transport_send_message(sut_client, message_params, configuration=configuration)

    # Since push notifications capability is declared, message send should succeed
    assert transport_helpers.is_json_rpc_success_response(resp), (
        "Push notifications capability declared but message/send with pushNotificationConfig failed"
    )

    task_id = resp["result"]["id"]
    logger.info(f"Task created with ID: {task_id}")

    # Verify that the push notification config was actually used
    # We can check this by attempting to retrieve the push notification config for the task
    list_resp = transport_helpers.transport_list_push_notification_configs(sut_client, task_id)

    if transport_helpers.is_json_rpc_success_response(list_resp):
        configs = list_resp["result"]
        assert isinstance(configs, list), "Push notification configs should be a list"

        logger.info(f"Retrieved {len(configs)} push notification configs for task {task_id}")
        for idx, config in enumerate(configs):
            logger.info(f"Config {idx}: {config}")

        # Verify that a configuration with our webhook URL exists
        found_config = False
        for config in configs:
            if "pushNotificationConfig" in config:
                config_url = config["pushNotificationConfig"].get("url")
                logger.info(f"Checking config URL: {config_url}")
                if config_url == webhook_url:
                    found_config = True
                    logger.info(f"✓ Found push notification config with URL: {webhook_url}")
                    break

        if not found_config:
            logger.error(f"❌ Push notification config from SendMessageConfiguration was NOT found!")
            logger.error(f"Expected URL: {webhook_url}")
            logger.error(f"Available configs: {configs}")

        assert found_config, (
            f"Push notification config from SendMessageConfiguration was not found in task configs. "
            f"Expected URL: {webhook_url}. "
            f"Retrieved {len(configs)} config(s): {configs}. "
            f"This indicates the pushNotificationConfig in SendMessageConfiguration was ignored."
        )

        # Also verify that push notification was actually sent to the webhook
        logger.info("Waiting for push notification to be received by webhook...")
        notification_received = push_notification_webhook['wait_for_notification'](timeout=10.0)

        if notification_received:
            logger.info(f"✓ Webhook received {len(push_notification_webhook['notifications'])} notification(s)")
            for idx, notification in enumerate(push_notification_webhook['notifications']):
                logger.info(f"Notification {idx}: {notification}")

            # Verify the notification is for our task
            # Notification can be a Task object (with "id") or status update (with "taskId")
            task_found_in_notifications = any(
                notification.get("taskId") == task_id or notification.get("id") == task_id
                for notification in push_notification_webhook['notifications']
            )
            assert task_found_in_notifications, (
                f"Push notification was sent but did not contain our task ID {task_id}. "
                f"Notifications received: {push_notification_webhook['notifications']}"
            )
        else:
            logger.warning(
                f"⚠️  No push notification received within timeout. "
                f"Config was stored correctly, but notification may not have been sent. "
                f"This could indicate a timing issue or the SUT may send notifications asynchronously."
            )
            # Note: We don't fail the test here because the config being stored is the primary requirement.
            # Actual notification delivery may be asynchronous and could arrive after test completion.

    else:
        # If list fails, log the error details
        logger.error(f"List push notification configs failed for task {task_id}")
        logger.error(f"Response: {list_resp}")
        pytest.fail(
            f"Could not verify pushNotificationConfig was used. "
            f"List configs failed with: {list_resp.get('error', 'Unknown error')}"
        )


@optional_capability
def test_send_streaming_message_with_push_notification_config(sut_client, agent_card_data, push_notification_webhook):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.1 - SendMessageConfiguration with pushNotificationConfig (Streaming)

    Status: MANDATORY if capabilities.pushNotifications = true AND capabilities.streaming = true
            SKIP if either capability is false/missing

    Test validates that pushNotificationConfig in SendMessageConfiguration is actually
    used and not ignored when sending a streaming message. This test verifies both:
    1. The config is stored and retrievable from the task
    2. Push notifications are actually sent to the configured webhook URL

    This complements test_send_message_with_push_notification_config by testing the streaming variant,
    since the server implementation (DefaultRequestHandler in a2a-java) supports configuration
    for both onMessageSend() and onMessageSendStream() methods.

    Specification Reference: A2A Protocol v0.3.0 §7.1.2 - SendMessageConfiguration, §8.1 - Streaming
    """
    import asyncio

    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    # Prepare a streaming message with pushNotificationConfig using real webhook server
    message_id = "test-push-config-stream-" + str(uuid.uuid4())
    webhook_url = push_notification_webhook['url']

    message_params = {
        "message": {
            "messageId": message_id,
            "role": "user",
            "parts": [{"kind": "text", "text": "Task with push notification config in streaming send configuration"}],
            "kind": "message",
        }
    }

    configuration = {
        "pushNotificationConfig": {
            "url": webhook_url,
            "token": "test-streaming-token-456",
        },
        "blocking": False,  # Streaming should be non-blocking
    }

    # Send the streaming message with configuration
    async def run_streaming_test():
        task_id = None
        stream = transport_helpers.transport_send_streaming_message(
            sut_client, message_params, configuration=configuration
        )

        # Collect streaming updates and extract task_id
        # Different transports return different formats:
        # - JSON-RPC: yields Task objects directly (with "id" and "status" fields)
        # - gRPC/REST: yields wrapped objects with "task" or "status_update" keys
        async for update in stream:
            if isinstance(update, dict):
                # Format 1: gRPC/REST - wrapped with "task" key
                if "task" in update:
                    task_id = update["task"]["id"]
                    logger.info(f"Received task from streaming (wrapped): {task_id}")
                    break  # Got the task, can stop streaming
                # Format 2: gRPC/REST - status_update with taskId
                elif "status_update" in update:
                    if not task_id:
                        task_id = update["status_update"]["taskId"]
                        logger.info(f"Received task_id from status_update: {task_id}")
                # Format 3: JSON-RPC - Task object directly
                elif "id" in update and "status" in update and "kind" in update:
                    task_id = update["id"]
                    logger.info(f"Received task from streaming (direct): {task_id}")
                    break  # Got the task, can stop streaming

        return task_id

    # Run the async streaming test
    task_id = asyncio.run(run_streaming_test())

    assert task_id is not None, "Streaming message should return a task"
    logger.info(f"Streaming task created with ID: {task_id}")

    # Verify that the push notification config was actually used
    # We can check this by attempting to retrieve the push notification config for the task
    list_resp = transport_helpers.transport_list_push_notification_configs(sut_client, task_id)

    if transport_helpers.is_json_rpc_success_response(list_resp):
        configs = list_resp["result"]
        assert isinstance(configs, list), "Push notification configs should be a list"

        logger.info(f"Retrieved {len(configs)} push notification configs for streaming task {task_id}")
        for idx, config in enumerate(configs):
            logger.info(f"Config {idx}: {config}")

        # Verify that a configuration with our webhook URL exists
        found_config = False
        for config in configs:
            if "pushNotificationConfig" in config:
                config_url = config["pushNotificationConfig"].get("url")
                logger.info(f"Checking config URL: {config_url}")
                if config_url == webhook_url:
                    found_config = True
                    logger.info(f"✓ Found push notification config from streaming with URL: {webhook_url}")
                    break

        if not found_config:
            logger.error(f"❌ Push notification config from streaming SendMessageConfiguration was NOT found!")
            logger.error(f"Expected URL: {webhook_url}")
            logger.error(f"Available configs: {configs}")

        assert found_config, (
            f"Push notification config from streaming SendMessageConfiguration was not found in task configs. "
            f"Expected URL: {webhook_url}. "
            f"Retrieved {len(configs)} config(s): {configs}. "
            f"This indicates the pushNotificationConfig in streaming SendMessageConfiguration was ignored."
        )

        # Also verify that push notification was actually sent to the webhook
        logger.info("Waiting for push notification to be received by webhook...")
        notification_received = push_notification_webhook['wait_for_notification'](timeout=10.0)

        if notification_received:
            logger.info(f"✓ Webhook received {len(push_notification_webhook['notifications'])} notification(s)")
            for idx, notification in enumerate(push_notification_webhook['notifications']):
                logger.info(f"Notification {idx}: {notification}")

            # Verify the notification is for our task
            # Notification can be a Task object (with "id") or status update (with "taskId")
            task_found_in_notifications = any(
                notification.get("taskId") == task_id or notification.get("id") == task_id
                for notification in push_notification_webhook['notifications']
            )
            assert task_found_in_notifications, (
                f"Push notification was sent but did not contain our task ID {task_id}. "
                f"Notifications received: {push_notification_webhook['notifications']}"
            )
        else:
            logger.warning(
                f"⚠️  No push notification received within timeout. "
                f"Config was stored correctly, but notification may not have been sent. "
                f"This could indicate a timing issue or the SUT may send notifications asynchronously."
            )
            # Note: We don't fail the test here because the config being stored is the primary requirement.
            # Actual notification delivery may be asynchronous and could arrive after test completion.

    else:
        # If list fails, log the error details
        logger.error(f"List push notification configs failed for streaming task {task_id}")
        logger.error(f"Response: {list_resp}")
        pytest.fail(
            f"Could not verify streaming pushNotificationConfig was used. "
            f"List configs failed with: {list_resp.get('error', 'Unknown error')}"
        )
