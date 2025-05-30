# A2A Protocol Mandatory Tests

These tests validate A2A specification MUST requirements.

**Status**: MANDATORY - ALL must pass for A2A compliance

## Test Files
- `test_agent_card.py` - Agent Card availability and mandatory fields
- `test_message_send_method.py` - Core message/send functionality
- `test_tasks_get_method.py` - Task retrieval with required parameters
- `test_tasks_cancel_method.py` - Task cancellation functionality
- `test_state_transitions.py` - Required state management features

## Failure Impact
Any failure in these tests means the implementation is **NOT A2A compliant**.
