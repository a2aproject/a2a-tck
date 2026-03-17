Feature: Core Operations
  SUT executor behavior for core A2A TCK requirements.

  Each scenario defines what the agent executor does when it receives
  a message with a messageId matching the specified prefix. Standard
  A2A protocol behavior (error handling, capability validation,
  contextId/taskId semantics) is handled by the SDK framework.

  The messageId prefix is the in-band signal linking TCK tests to SUT
  behavior -- no side-channel API is needed.

  # ---------------------------------------------------------------------------
  # Task completion
  # ---------------------------------------------------------------------------

  # Default behavior: complete the task with a message.
  # Used by: CORE-SEND-001, CORE-SEND-002 (setup), CORE-EXECUTION-MODE-001,
  # CORE-EXECUTION-MODE-002, CORE-MULTI-001/001a/002/002a/003,
  # CORE-GET-001 (setup), CORE-CANCEL-002 (setup), CORE-MULTI-005/006 (setup),
  # STREAM-SUB-002/003 (setup).
  Scenario: Complete the task
    When a message is received with prefix "tck-complete-task"
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

  Scenario: Task with file URL artifact
    When a message is received with prefix "tck-artifact-file-url"
    Then complete the task
    And add an artifact with a file url "https://example.com/output.txt" named "output.txt" with media type "text/plain"

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

  # Used by: CORE-CANCEL-001 (setup — non-terminal task for cancel test).
  Scenario: Task requiring user input
    When a message is received with prefix "tck-input-required"
    Then update the task status to "input_required"

  Scenario: Task rejected by executor
    When a message is received with prefix "tck-reject-task"
    Then reject with error "rejected"
