"""
A2A v1.0 ListTasks Method Testing

Comprehensive test suite for the ListTasks operation as specified in
A2A v1.0 specification Section 3.1.4.

Tests cover:
- Basic listing functionality
- Filtering (contextId, status, statusTimestampAfter)
- Pagination (pageSize, pageToken, totalSize)
- History limiting (historyLength parameter)
- Artifact inclusion (includeArtifacts parameter)
- Edge cases and error handling
- Cross-transport consistency (JSON-RPC, gRPC, REST)

References:
- A2A v1.0 Specification §3.1.4: ListTasks
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from tck.transport.base_client import BaseTransportClient
from tests.markers import mandatory_protocol, optional_capability
from tests.utils.transport_helpers import (
    transport_send_message,
    transport_list_tasks,
    transport_get_task,
    is_json_rpc_success_response,
    is_json_rpc_error_response,
    generate_test_message_id,
)


def create_test_task(client: BaseTransportClient, text: str, context_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Helper to create a test task with optional context ID.

    Waits for the task to reach WORKING state since the AgentExecutor
    transitions tasks asynchronously in a background thread.

    Returns:
        Task dict containing id, contextId, status, etc.
    """
    message_id = generate_test_message_id("list-test")
    params = {
        "message": {
            "messageId": message_id,
            "role": "ROLE_USER",
            "parts": [{"text": text}],
        }
    }

    if context_id:
        params["message"]["contextId"] = context_id

    resp = transport_send_message(client, params)
    assert is_json_rpc_success_response(resp), f"Task creation failed: {resp}"

    # Extract task from response
    # A2A v1.0: SendMessage returns {"result": {"task": {...}}}
    result = resp.get("result", resp)
    task = result["task"]
    task_id = task["id"]

    # Wait for task to reach WORKING state (background thread transition)
    # AgentExecutor immediately transitions SUBMITTED → WORKING in background thread
    max_wait_seconds = 5
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        # Get current task state
        get_resp = transport_get_task(client, task_id)
        if is_json_rpc_success_response(get_resp):
            current_task = get_resp.get("result", get_resp)
            current_state = current_task.get("status", {}).get("state")
            if current_state == "TASK_STATE_WORKING":
                return current_task
        time.sleep(0.1)

    # Timeout - fail the test
    raise AssertionError(f"Task {task_id} did not reach WORKING state within {max_wait_seconds} seconds. Last state: {task.get('status', {}).get('state')}")


class TestBasicListing:
    """
    Test suite for basic ListTasks functionality.

    Validates:
    - Listing all tasks
    - Empty list handling
    - Task structure compliance
    """

    @mandatory_protocol
    def test_list_all_tasks(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - List All Tasks

        Test that ListTasks returns all accessible tasks when called without filters.

        Validates:
        - Method is available on all transports
        - Response follows ListTasksResult schema
        - Tasks array is returned
        - Response includes totalSize and pageSize

        Specification Reference: A2A v1.0 §3.1.4 ListTasksResult
        """
        # Create at least one task to ensure non-empty list
        task = create_test_task(sut_client, "Test task for listing")
        task_id = task["id"]

        # List all tasks
        resp = transport_list_tasks(sut_client)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)

        # Validate ListTasksResult structure (§3.1.4)
        assert "tasks" in result, "Response must include 'tasks' array"
        assert "totalSize" in result, "Response must include 'totalSize'"
        assert "pageSize" in result, "Response must include 'pageSize'"
        assert "nextPageToken" in result, "Response must include 'nextPageToken'"

        # Validate types
        assert isinstance(result["tasks"], list), "'tasks' must be an array"
        assert isinstance(result["totalSize"], int), "'totalSize' must be an integer"
        assert isinstance(result["pageSize"], int), "'pageSize' must be an integer"

        # Should include our created task
        task_ids = [t["id"] for t in result["tasks"]]
        assert task_id in task_ids, f"Created task {task_id} not found in list"

        # Validate task structure
        our_task = next(t for t in result["tasks"] if t["id"] == task_id)
        assert "status" in our_task, "Task must include 'status' field"
        assert "contextId" in our_task, "Task must include 'contextId' field"

    @mandatory_protocol
    def test_list_tasks_empty_when_none_exist(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Empty List Handling

        Test that ListTasks returns empty array when no tasks exist (or none match filters).

        Uses a unique contextId to ensure we get zero results.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksResult
        """
        # Use a unique context ID that shouldn't have any tasks
        unique_context = f"empty-test-{int(time.time() * 1000)}"

        resp = transport_list_tasks(sut_client, context_id=unique_context)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)

        # Should have empty tasks array
        assert result["tasks"] == [], "Tasks array should be empty for non-existent context"
        assert result["totalSize"] == 0, "totalSize should be 0 when no tasks match"
        assert result["pageSize"] == 0, "pageSize should be 0 when no tasks returned"
        # Per spec: nextPageToken MUST be empty string when no more results
        assert result["nextPageToken"] == "", \
            "nextPageToken MUST be empty string when no more results (not None)"

    @mandatory_protocol
    def test_list_tasks_validates_required_fields(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Required Fields Validation

        Test that each task in the list contains all required fields per Task schema.

        Specification Reference: A2A v1.0 §6.1 Task Object
        """
        # Create a task
        task = create_test_task(sut_client, "Task for field validation")

        # List tasks
        resp = transport_list_tasks(sut_client)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)
        assert len(result["tasks"]) > 0, "Should have at least one task"

        # Validate each task has required fields
        for task in result["tasks"]:
            assert "id" in task, "Task must have 'id' field"
            assert "status" in task, "Task must have 'status' field"

            # Status must have required fields
            assert "state" in task["status"], "Task status must have 'state' field"
            # Note: timestamp is optional per A2A spec

    @mandatory_protocol
    def test_list_tasks_sorted_by_timestamp_descending(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Sort Order Requirement

        Test that tasks are sorted by last updated timestamp in descending order
        (most recently updated tasks first).

        Specification Reference: A2A v1.0 §3.1.4 - "Tasks MUST be sorted by their
        status timestamp time in descending order"
        """
        # Create multiple tasks with slight delays to ensure different timestamps
        task1 = create_test_task(sut_client, "First task")
        time.sleep(0.2)
        task2 = create_test_task(sut_client, "Second task")
        time.sleep(0.2)
        task3 = create_test_task(sut_client, "Third task")

        # List all tasks
        resp = transport_list_tasks(sut_client)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)
        tasks = result["tasks"]

        # Find our created tasks in the results
        our_task_ids = {task1["id"], task2["id"], task3["id"]}
        our_tasks = [t for t in tasks if t["id"] in our_task_ids]

        # Should have all three tasks
        assert len(our_tasks) == 3, f"Expected 3 tasks, found {len(our_tasks)}"

        # Tasks should be in descending order by timestamp (newest first)
        # task3 should come before task2, task2 before task1
        task_positions = {t["id"]: idx for idx, t in enumerate(our_tasks)}

        assert task_positions[task3["id"]] < task_positions[task2["id"]], \
            "Task3 (newest) should appear before Task2"
        assert task_positions[task2["id"]] < task_positions[task1["id"]], \
            "Task2 should appear before Task1 (oldest)"


class TestFiltering:
    """
    Test suite for ListTasks filtering parameters.

    Validates:
    - contextId filtering
    - status filtering
    - statusTimestampAfter filtering
    - Combined filters
    """

    @mandatory_protocol
    def test_filter_by_context_id(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - contextId Filter

        Test that contextId parameter correctly filters tasks to a specific context.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create tasks with different context IDs
        context1 = f"context-1-{int(time.time() * 1000)}"
        context2 = f"context-2-{int(time.time() * 1000)}"

        task1 = create_test_task(sut_client, "Task in context 1", context_id=context1)
        task2 = create_test_task(sut_client, "Task in context 2", context_id=context2)

        # Filter by context1
        resp = transport_list_tasks(sut_client, context_id=context1)
        assert is_json_rpc_success_response(resp), f"tasks/list with contextId failed: {resp}"

        result = resp.get("result", resp)

        # Should only include tasks from context1
        for task in result["tasks"]:
            assert task["contextId"] == context1, \
                f"All tasks should have contextId '{context1}', got '{task['contextId']}'"

        # Should include task1, not task2
        task_ids = [t["id"] for t in result["tasks"]]
        assert task1["id"] in task_ids, f"Task1 should be in filtered results"
        assert task2["id"] not in task_ids, f"Task2 should NOT be in filtered results"

    @mandatory_protocol
    def test_filter_by_status(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - status Filter

        Test that status parameter correctly filters tasks by their current state.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create a task
        task = create_test_task(sut_client, "Task for status filtering")
        task_id = task["id"]
        status_state = task["status"]["state"]

        # Filter by the task's status
        resp = transport_list_tasks(sut_client, status=status_state)
        assert is_json_rpc_success_response(resp), f"tasks/list with status failed: {resp}"

        result = resp.get("result", resp)

        # All returned tasks should have the requested status
        for task in result["tasks"]:
            assert task["status"]["state"] == status_state, \
                f"All tasks should have status '{status_state}', got '{task['status']['state']}'"

        # Should include our created task
        task_ids = [t["id"] for t in result["tasks"]]
        assert task_id in task_ids, f"Task {task_id} with status '{status_state}' should be in results"

    @mandatory_protocol
    def test_filter_by_last_updated_after(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - statusTimestampAfter Filter

        Test that statusTimestampAfter parameter filters tasks updated after a timestamp.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Get current timestamp in milliseconds
        timestamp_before = datetime.now(timezone.utc).isoformat()

        # Wait a bit to ensure timestamp difference
        time.sleep(0.1)

        # Create a task after the timestamp
        task = create_test_task(sut_client, "Task created after timestamp")
        task_id = task["id"]

        # Filter by statusTimestampAfter
        resp = transport_list_tasks(sut_client, status_timestamp_after=timestamp_before)
        assert is_json_rpc_success_response(resp), f"tasks/list with statusTimestampAfter failed: {resp}"

        result = resp.get("result", resp)

        # Should include our newly created task
        task_ids = [t["id"] for t in result["tasks"]]
        assert task_id in task_ids, f"Task {task_id} created after timestamp should be in results"

        # All tasks should have status.timestamp >= statusTimestampAfter
        for task in result["tasks"]:
            # Parse timestamp from ISO 8601 string to compare
            # Note: This assumes status.timestamp is in ISO 8601 format
            # If it's already in milliseconds, adjust accordingly
            pass  # Validation can be added based on timestamp format

    @mandatory_protocol
    def test_combined_filters(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Combined Filters

        Test that multiple filters can be applied together (AND logic).

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create tasks with specific context and status
        context_id = f"combined-test-{int(time.time() * 1000)}"

        task = create_test_task(sut_client, "Task for combined filtering", context_id=context_id)
        task_id = task["id"]
        status_state = task["status"]["state"]

        # Apply both contextId and status filters
        resp = transport_list_tasks(sut_client, context_id=context_id, status=status_state)
        assert is_json_rpc_success_response(resp), f"tasks/list with combined filters failed: {resp}"

        result = resp.get("result", resp)

        # All tasks should match both filters
        for task in result["tasks"]:
            assert task["contextId"] == context_id, \
                f"Task should have contextId '{context_id}'"
            assert task["status"]["state"] == status_state, \
                f"Task should have status '{status_state}'"

        # Should include our created task
        task_ids = [t["id"] for t in result["tasks"]]
        assert task_id in task_ids, f"Task {task_id} matching both filters should be in results"


class TestPagination:
    """
    Test suite for ListTasks pagination.

    Validates:
    - Default page size (50)
    - Custom page size
    - Page token navigation
    - Last page detection
    - Total size accuracy
    """

    @mandatory_protocol
    def test_default_page_size(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Default Page Size

        Test that default pageSize is 50 when not specified.

        Note: This test only validates the behavior if there are enough tasks.
        If fewer than 50 tasks exist, pageSize will match the actual count.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # List tasks without specifying pageSize
        resp = transport_list_tasks(sut_client)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)

        # If totalSize > 50, pageSize should be 50 (default)
        # If totalSize <= 50, pageSize should equal totalSize
        if result["totalSize"] > 50:
            assert result["pageSize"] == 50, "Default pageSize should be 50"
            assert len(result["tasks"]) == 50, "Should return 50 tasks when totalSize > 50"
        else:
            assert result["pageSize"] == result["totalSize"], \
                "pageSize should equal totalSize when totalSize <= 50"
            assert len(result["tasks"]) == result["totalSize"], \
                "Should return all tasks when totalSize <= 50"

    @mandatory_protocol
    def test_custom_page_size(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Custom Page Size

        Test that pageSize parameter controls the number of tasks returned.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create multiple tasks to ensure we have enough for pagination
        context_id = f"pagination-test-{int(time.time() * 1000)}"
        for i in range(5):
            create_test_task(sut_client, f"Task {i} for pagination", context_id=context_id)

        # Request with pageSize=2
        resp = transport_list_tasks(sut_client, context_id=context_id, page_size=2)
        assert is_json_rpc_success_response(resp), f"tasks/list with pageSize failed: {resp}"

        result = resp.get("result", resp)

        # Should return at most 2 tasks
        assert result["pageSize"] == min(2, result["totalSize"]), \
            f"pageSize should be 2 or totalSize, whichever is smaller"
        assert len(result["tasks"]) == result["pageSize"], \
            "Number of tasks should match pageSize"

        # If there are more than 2 tasks total, should have nextPageToken
        if result["totalSize"] > 2:
            assert result["nextPageToken"] is not None and result["nextPageToken"] != "", \
                "Should have nextPageToken when more results available"

    @mandatory_protocol
    def test_page_token_navigation(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Page Token Navigation

        Test that pageToken allows navigation through multiple pages of results.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create multiple tasks
        context_id = f"pagination-nav-test-{int(time.time() * 1000)}"
        task_ids = []
        for i in range(5):
            task = create_test_task(sut_client, f"Task {i} for nav test", context_id=context_id)
            task_ids.append(task["id"])

        # Get first page with pageSize=2
        resp1 = transport_list_tasks(sut_client, context_id=context_id, page_size=2)
        assert is_json_rpc_success_response(resp1), f"First page request failed: {resp1}"

        result1 = resp1.get("result", resp1)
        assert result1["pageSize"] == 2, "First page should have 2 tasks"

        # Should have nextPageToken since we have more tasks
        assert result1["nextPageToken"] is not None and result1["nextPageToken"] != "", \
            "Should have nextPageToken for next page"

        page1_ids = [t["id"] for t in result1["tasks"]]

        # Get second page using nextPageToken
        resp2 = transport_list_tasks(
            sut_client,
            context_id=context_id,
            page_size=2,
            page_token=result1["nextPageToken"]
        )
        assert is_json_rpc_success_response(resp2), f"Second page request failed: {resp2}"

        result2 = resp2.get("result", resp2)
        page2_ids = [t["id"] for t in result2["tasks"]]

        # Pages should not overlap
        assert not set(page1_ids) & set(page2_ids), "Pages should not contain duplicate tasks"

        # Combined pages should be subset of our created tasks
        all_returned_ids = page1_ids + page2_ids
        for returned_id in all_returned_ids:
            assert returned_id in task_ids, f"Returned task {returned_id} should be one we created"

    @mandatory_protocol
    def test_last_page_detection(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Last Page Detection

        Test that nextPageToken is None/empty on the last page of results.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksResult
        """
        # Create exactly 3 tasks
        context_id = f"last-page-test-{int(time.time() * 1000)}"
        for i in range(3):
            create_test_task(sut_client, f"Task {i} for last page test", context_id=context_id)

        # Request all tasks with pageSize=10 (more than we have)
        resp = transport_list_tasks(sut_client, context_id=context_id, page_size=10)
        assert is_json_rpc_success_response(resp), f"Last page request failed: {resp}"

        result = resp.get("result", resp)

        # Should have all 3 tasks
        assert result["totalSize"] == 3, "Should have 3 total tasks"
        assert result["pageSize"] == 3, "Should return all 3 tasks"

        # Per spec: nextPageToken MUST be empty string when no more results
        assert result["nextPageToken"] == "", \
            "nextPageToken MUST be empty string on last page (not None)"

    @mandatory_protocol
    def test_total_size_accuracy(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Total Size Accuracy

        Test that totalSize accurately reflects all matching tasks before pagination.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksResult
        """
        # Create known number of tasks
        context_id = f"total-size-test-{int(time.time() * 1000)}"
        num_tasks = 5
        for i in range(num_tasks):
            create_test_task(sut_client, f"Task {i} for total size test", context_id=context_id)

        # Request with small pageSize
        resp = transport_list_tasks(sut_client, context_id=context_id, page_size=2)
        assert is_json_rpc_success_response(resp), f"Request failed: {resp}"

        result = resp.get("result", resp)

        # totalSize should reflect all tasks, not just the page
        assert result["totalSize"] == num_tasks, \
            f"totalSize should be {num_tasks}, got {result['totalSize']}"

        # pageSize should be 2 (the requested size)
        assert result["pageSize"] == 2, "pageSize should be 2"

        # Should have nextPageToken since we have more results
        assert result["nextPageToken"] is not None and result["nextPageToken"] != "", \
            "Should have nextPageToken when more results available"


class TestHistoryLimiting:
    """
    Test suite for historyLength parameter.

    Validates:
    - historyLength=0 (no history)
    - Custom historyLength values
    - historyLength larger than actual history
    - Consistency across pagination
    """

    @mandatory_protocol
    def test_history_length_zero(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - History Length Zero (Default)

        Test that historyLength=0 returns tasks without history array (or empty).

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create a task
        task = create_test_task(sut_client, "Task for history test")

        # List with historyLength=0 (default)
        resp = transport_list_tasks(sut_client, history_length=0)
        assert is_json_rpc_success_response(resp), f"tasks/list with historyLength=0 failed: {resp}"

        result = resp.get("result", resp)

        # Tasks should have no history or empty history
        for task in result["tasks"]:
            if "history" in task:
                assert len(task["history"]) == 0, \
                    "Tasks should have empty history when historyLength=0"

    @mandatory_protocol
    def test_history_length_custom(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Custom History Length

        Test that historyLength parameter limits the number of messages returned.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create a task
        task = create_test_task(sut_client, "Task for history length test")

        # List with historyLength=3
        resp = transport_list_tasks(sut_client, history_length=3)
        assert is_json_rpc_success_response(resp), f"tasks/list with historyLength=3 failed: {resp}"

        result = resp.get("result", resp)

        # Tasks with history should have at most 3 messages
        for task in result["tasks"]:
            if "history" in task and task["history"]:
                assert len(task["history"]) <= 3, \
                    f"Task history should have at most 3 messages, got {len(task['history'])}"

    @mandatory_protocol
    def test_history_length_exceeds_actual(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - History Length Exceeds Actual

        Test that requesting more history than exists returns all available history.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create a task (will have 1-2 messages in history typically)
        task = create_test_task(sut_client, "Task for history test")

        # List with very large historyLength
        resp = transport_list_tasks(sut_client, history_length=100)
        assert is_json_rpc_success_response(resp), f"tasks/list with large historyLength failed: {resp}"

        result = resp.get("result", resp)

        # Should return all available history without error
        # Just validate it doesn't fail - actual history count depends on implementation
        assert "tasks" in result, "Response should include tasks"


class TestArtifactInclusion:
    """
    Test suite for includeArtifacts parameter.

    Validates:
    - includeArtifacts=false (default)
    - includeArtifacts=true
    - Consistency across pagination
    """

    @mandatory_protocol
    def test_artifacts_excluded_by_default(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Artifacts Excluded by Default

        Test that includeArtifacts defaults to false, excluding artifacts from response.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create a task
        task = create_test_task(sut_client, "Task for artifact test")

        # List without specifying includeArtifacts (default=false)
        resp = transport_list_tasks(sut_client)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)

        # Per spec: artifacts should not be returned when includeArtifacts is false (default)
        # Accept either: field not present OR field present as empty array
        for task in result["tasks"]:
            artifacts = task.get("artifacts")
            assert artifacts is None or artifacts == [], \
                f"Artifacts must be either absent or empty array when includeArtifacts=false (default), " \
                f"got: {artifacts}"

    @mandatory_protocol
    def test_artifacts_included_when_requested(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Artifacts Included When Requested

        Test that includeArtifacts=true includes artifacts in the response.

        Note: This test validates the parameter is accepted. Actual artifact presence
        depends on whether tasks have artifacts.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Create a task
        task = create_test_task(sut_client, "Task for artifact inclusion test")

        # List with includeArtifacts=true
        resp = transport_list_tasks(sut_client, include_artifacts=True)
        assert is_json_rpc_success_response(resp), f"tasks/list with includeArtifacts=true failed: {resp}"

        result = resp.get("result", resp)

        # Should succeed - actual artifact content depends on implementation
        assert "tasks" in result, "Response should include tasks"

        # If any task has artifacts, validate it's an array
        for task in result["tasks"]:
            if "artifacts" in task and task["artifacts"]:
                assert isinstance(task["artifacts"], list), "Artifacts should be an array"


class TestEdgeCasesAndErrors:
    """
    Test suite for edge cases and error handling.

    Validates:
    - Invalid pageToken
    - Invalid status value
    - Negative pageSize
    - Negative historyLength
    - Out-of-range pageSize
    - Invalid statusTimestampAfter
    """

    @mandatory_protocol
    def test_invalid_page_token_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Invalid Page Token Error

        Test that invalid pageToken returns proper error (-32602 InvalidParamsError).

        Specification Reference: A2A v1.0 §3.1.4 Error Cases
        """
        # Use obviously invalid page token
        resp = transport_list_tasks(sut_client, page_token="invalid-token-xyz")

        # Should return error
        assert is_json_rpc_error_response(resp), "Invalid pageToken should return error"

        error = resp.get("error", {})
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"Invalid pageToken should return -32602, got {error.get('code')}"

    @mandatory_protocol
    def test_invalid_status_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Invalid Status Error

        Test that invalid status value returns proper error (-32602 InvalidParamsError).

        Specification Reference: A2A v1.0 §3.1.4 Error Cases
        """
        # Use invalid status value
        resp = transport_list_tasks(sut_client, status="INVALID_STATUS")

        # Should return error
        assert is_json_rpc_error_response(resp), "Invalid status should return error"

        error = resp.get("error", {})
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"Invalid status should return -32602, got {error.get('code')}"

    @mandatory_protocol
    def test_negative_page_size_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Negative Page Size Error

        Test that negative pageSize returns proper error (-32602 InvalidParamsError).

        Specification Reference: A2A v1.0 §3.1.4 Error Cases
        """
        # Use negative pageSize
        resp = transport_list_tasks(sut_client, page_size=-1)

        # Should return error
        assert is_json_rpc_error_response(resp), "Negative pageSize should return error"

        error = resp.get("error", {})
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"Negative pageSize should return -32602, got {error.get('code')}"

    @mandatory_protocol
    def test_zero_page_size_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Zero Page Size Error

        Test that pageSize=0 returns proper error (-32602 InvalidParamsError).
        Per spec: "pageSize must be between 1 and 100"

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams
        """
        # Use pageSize=0
        resp = transport_list_tasks(sut_client, page_size=0)

        # Should return error
        assert is_json_rpc_error_response(resp), "pageSize=0 should return error"

        error = resp.get("error", {})
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"pageSize=0 should return -32602, got {error.get('code')}"

    @mandatory_protocol
    def test_out_of_range_page_size_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Out of Range Page Size Error

        Test that pageSize > 100 returns proper error (-32602 InvalidParamsError).

        Specification Reference: A2A v1.0 §3.1.4 Error Cases
        """
        # Use pageSize > 100
        resp = transport_list_tasks(sut_client, page_size=101)

        # Should return error
        assert is_json_rpc_error_response(resp), "pageSize > 100 should return error"

        error = resp.get("error", {})
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"pageSize > 100 should return -32602, got {error.get('code')}"

    @mandatory_protocol
    def test_default_page_size_is_50(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Default Page Size

        Test that when pageSize is not specified, it defaults to 50.

        Specification Reference: A2A v1.0 §3.1.4 ListTasksParams -
        "Defaults to 50 if not specified"
        """
        # Create exactly 60 tasks to ensure we can test the default pageSize
        context_id = f"default-pagesize-test-{int(time.time() * 1000)}"
        for i in range(60):
            create_test_task(sut_client, f"Task {i} for default pageSize test", context_id=context_id)

        # List without specifying pageSize (should default to 50)
        resp = transport_list_tasks(sut_client, context_id=context_id)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)

        # Should return exactly 50 tasks (the default pageSize)
        assert result["totalSize"] == 60, f"Should have 60 total tasks, got {result['totalSize']}"
        assert result["pageSize"] == 50, \
            f"Default pageSize should be 50, got {result['pageSize']}"
        assert len(result["tasks"]) == 50, \
            f"Should return 50 tasks with default pageSize, got {len(result['tasks'])}"
        assert result["nextPageToken"] != "", \
            "Should have nextPageToken since there are more results"

    @mandatory_protocol
    def test_negative_history_length_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Negative History Length Error

        Test that negative historyLength returns proper error (-32602 InvalidParamsError).

        Specification Reference: A2A v1.0 §3.1.4 Error Cases
        """
        # Use negative historyLength
        resp = transport_list_tasks(sut_client, history_length=-1)

        # Should return error
        assert is_json_rpc_error_response(resp), "Negative historyLength should return error"

        error = resp.get("error", {})
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"Negative historyLength should return -32602, got {error.get('code')}"

    @mandatory_protocol
    def test_invalid_timestamp_error(self, sut_client: BaseTransportClient):
        """
        MANDATORY: A2A v1.0 §3.1.4 - Invalid Timestamp Error

        Test that invalid statusTimestampAfter timestamp returns proper error.

        Specification Reference: A2A v1.0 §3.1.4 Error Cases
        """
        # Use invalid timestamp (negative value)
        resp = transport_list_tasks(sut_client, status_timestamp_after=-1)

        # Should return error
        assert is_json_rpc_error_response(resp), "Invalid timestamp should return error"

        error = resp.get("error", {})
        print(error)
        # Should be InvalidParamsError (-32602)
        assert error.get("code") == -32602, \
            f"Invalid timestamp should return -32602, got {error.get('code')}"


class TestTransportConsistency:
    """
    Test suite for cross-transport consistency.

    Validates:
    - Same results across JSON-RPC, gRPC, REST
    - Same pagination behavior
    - Same filtering logic
    """

    @optional_capability
    def test_same_results_across_transports(self, sut_client: BaseTransportClient):
        """
        OPTIONAL: A2A v1.0 §3.4.1 - Cross-Transport Functional Equivalence

        Test that ListTasks returns consistent results across all transports.

        Note: This test requires multiple transport implementations to be available.

        Specification Reference: A2A v1.0 §3.4.1 Functional Equivalence
        """
        # This test would require access to multiple transport clients
        # For now, we validate that the response structure is correct
        # Actual cross-transport testing would be done in integration tests

        resp = transport_list_tasks(sut_client)
        assert is_json_rpc_success_response(resp), f"tasks/list failed: {resp}"

        result = resp.get("result", resp)

        # Validate response structure is consistent
        assert "tasks" in result
        assert "totalSize" in result
        assert "pageSize" in result
        assert "nextPageToken" in result
