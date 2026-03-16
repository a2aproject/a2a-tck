Feature: Core Operations
  SUT executor behavior for core A2A TCK requirements.

  Each scenario defines what the agent executor does when it receives
  a message with a messageId matching the specified prefix. Standard
  A2A protocol behavior (error handling, capability validation,
  contextId/taskId semantics) is handled by the SDK framework.

  The messageId prefix is the in-band signal linking TCK tests to SUT
  behavior -- no side-channel API is needed.

  # ---------------------------------------------------------------------------
  # SendMessage (Section 3.1.1)
  # ---------------------------------------------------------------------------

  Scenario: Basic task completion (CORE-SEND-001)
    When a message is received with prefix "tck-send-001"
    Then complete the task with the message "Hello from TCK"

  Scenario: Setup terminal task for rejection test (CORE-SEND-002)
    When a message is received with prefix "tck-terminal-send-002"
    Then complete the task with the message "Hello from TCK"

  # CORE-SEND-003: ContentTypeNotSupportedError is detected by the SDK framework
  # based on the agent card's supported input content types. No executor scenario needed.

  # ---------------------------------------------------------------------------
  # Artifacts (text, file, data parts)
  # ---------------------------------------------------------------------------

  Scenario: Task with text artifact
    When a message is received with prefix "tck-artifact-text"
    Then complete the task
    And add an artifact with a text part "Generated text content"

  Scenario: Task with file artifact
    When a message is received with prefix "tck-artifact-file"
    Then complete the task
    And add an artifact with a file part named "output.txt" with media type "text/plain"

  Scenario: Task with data artifact
    When a message is received with prefix "tck-artifact-data"
    Then complete the task
    And add an artifact with a data part:
      """json
      {"key": "value", "count": 42}
      """

  # ---------------------------------------------------------------------------
  # Message Response
  # ---------------------------------------------------------------------------

  Scenario: Return message instead of task
    When a message is received with prefix "tck-message-response"
    Then return a message with a text part "Direct message response"

  # ---------------------------------------------------------------------------
  # Task States
  # ---------------------------------------------------------------------------

  Scenario: Task requiring user input
    When a message is received with prefix "tck-input-required"
    Then update the task status to "input_required"

  Scenario: Task rejected by executor
    When a message is received with prefix "tck-reject-task"
    Then reject with error "rejected"

  # ---------------------------------------------------------------------------
  # CancelTask (Section 3.1.5)
  # ---------------------------------------------------------------------------

  Scenario: Cancelable task in non-terminal state (CORE-CANCEL-001)
    When a message is received with prefix "tck-cancel-001"
    Then update the task status to "input_required"

  # ---------------------------------------------------------------------------
  # Execution Mode (Section 3.2.2)
  # ---------------------------------------------------------------------------

  Scenario: Blocking mode task (CORE-EXECUTION-MODE-001)
    When a message is received with prefix "tck-block-001"
    Then complete the task with the message "Blocking response"

  Scenario: Non-blocking mode task (CORE-EXECUTION-MODE-002)
    When a message is received with prefix "tck-block-002"
    Then complete the task with the message "Non-blocking response"

  # ---------------------------------------------------------------------------
  # Generic Setup (for multi-operation tests)
  # ---------------------------------------------------------------------------

  # Used by create_completed_task() helper for: GetTask (CORE-GET-001),
  # CancelTask (CORE-CANCEL-002), multi-turn (CORE-MULTI-005,
  # CORE-MULTI-006, CORE-SEND-002), and SubscribeToTask lifecycle
  # (STREAM-SUB-002, STREAM-SUB-003).
  Scenario: Generic task creation for multi-operation setup
    When a message is received with prefix "tck-task-helper"
    Then complete the task with the message "Task helper response"
