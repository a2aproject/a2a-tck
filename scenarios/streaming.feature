Feature: Streaming Operations
  SUT executor behavior for streaming A2A TCK requirements.

  Each scenario defines what the agent executor does when it receives
  a streaming message with a messageId matching the specified prefix.

  # ---------------------------------------------------------------------------
  # SendStreamingMessage (Section 3.1.2)
  # ---------------------------------------------------------------------------

  Scenario: Basic streaming lifecycle (CORE-STREAM-001)
    When a streaming message is received with prefix "tck-stream-001"
    Then stream a status update to "working"
    And stream an artifact with a text part "Stream hello from TCK"
    And stream a status update to "completed"

  Scenario: Message-only stream (CORE-STREAM-002)
    When a streaming message is received with prefix "tck-stream-002"
    Then stream a status update to "completed"

  Scenario: Task lifecycle stream (CORE-STREAM-003)
    When a streaming message is received with prefix "tck-stream-003"
    Then stream a status update to "working"
    And stream an artifact with a text part "Stream task lifecycle"
    And stream a status update to "completed"

  # ---------------------------------------------------------------------------
  # Streaming Event Ordering (Section 3.5.2)
  # ---------------------------------------------------------------------------

  Scenario: Streaming with ordered status updates (STREAM-ORDER-001)
    When a streaming message is received with prefix "tck-stream-ordering-001"
    Then stream a status update to "working"
    And stream an artifact with a text part "Ordered output"
    And stream a status update to "completed"

  # ---------------------------------------------------------------------------
  # Streaming Artifacts
  # ---------------------------------------------------------------------------

  Scenario: Streaming with text artifact
    When a streaming message is received with prefix "tck-stream-artifact-text"
    Then stream a status update to "working"
    And stream an artifact with a text part "Streamed text content"
    And stream a status update to "completed"

  Scenario: Streaming with file artifact
    When a streaming message is received with prefix "tck-stream-artifact-file"
    Then stream a status update to "working"
    And stream an artifact with a file part named "output.txt" with media type "text/plain"
    And stream a status update to "completed"

  Scenario: Streaming with chunked artifact
    When a streaming message is received with prefix "tck-stream-artifact-chunked"
    Then stream a status update to "working"
    And stream an artifact chunk with a text part "chunk-1 "
    And stream a final artifact chunk with a text part "chunk-2"
    And stream a status update to "completed"

  # ---------------------------------------------------------------------------
  # Resubscription (long-running task)
  # ---------------------------------------------------------------------------

  Scenario: Long-running task for resubscription test
    When a streaming message is received with prefix "test-resubscribe-message-id"
    Then stream a status update to "working"
    And wait for 2x streaming timeout
    And stream a status update to "completed"
