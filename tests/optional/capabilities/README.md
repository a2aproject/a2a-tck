# Capability-Based Tests

These tests validate declared capabilities work correctly.

**Status**: CONDITIONAL MANDATORY - MUST pass IF capability is declared

## Test Files
- `test_streaming_methods.py` - Streaming capability validation
- `test_push_notification_config_methods.py` - Push notification capability
- `test_authentication.py` - Authentication scheme validation
- `test_transport_security.py` - Transport security validation

## Test Logic
- **SKIP** if capability not declared in Agent Card
- **MUST PASS** if capability is declared but not working
