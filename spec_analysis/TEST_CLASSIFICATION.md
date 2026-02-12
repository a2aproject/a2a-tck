# Test Classification by A2A Specification

## Mandatory Tests (MUST/SHALL Requirements)

### test_json_rpc_compliance.py - JSON-RPC 2.0 Compliance
- ✅ **test_rejects_malformed_json** - JSON-RPC 2.0 §4.2 MUST parse valid JSON
- ✅ **test_rejects_invalid_json_rpc_requests** - JSON-RPC 2.0 §4.1 MUST have required fields
- ✅ **test_rejects_unknown_method** - JSON-RPC 2.0 §4.3 MUST return -32601
- ✅ **test_rejects_invalid_params** - JSON-RPC 2.0 §4.3 MUST return -32602

### test_agent_card.py - Agent Card Mandatory Fields
- ✅ **test_agent_card_available** - A2A §2.1 "A2A Servers MUST make an Agent Card available"
- ✅ **test_mandatory_fields_present** - A2A §2.1 AgentCard MUST have required fields from schema
- ✅ **test_mandatory_field_types** - A2A §2.1 Fields MUST have correct types
- ❌ **test_capabilities_structure** - Optional (capabilities content is optional)
- ❌ **test_authentication_structure** - Optional (auth schemes are capability-based)

### test_message_send_method.py - Core Message Protocol
- ✅ **test_message_send_valid_text** - A2A §5.1 MUST support SendMessage with text
- ✅ **test_message_send_invalid_params** - A2A §5.1 MUST validate required fields
- ✅ **test_message_send_continue_task** - A2A §5.1 MUST support task continuation
- ✅ **test_message_send_continue_nonexistent_task** - A2A §5.1 MUST return TaskNotFoundError
- ❌ **test_message_send_valid_file_part** - Optional (file support is capability-based)
- ❌ **test_message_send_valid_data_part** - Optional (data support is capability-based)
- ❌ **test_message_send_valid_multiple_parts** - Optional (multiple parts capability-based)

### test_tasks_get_method.py - Task Retrieval Protocol  
- ✅ **test_tasks_get_valid** - A2A §7.3 MUST support tasks/get
- ✅ **test_tasks_get_with_history_length** - A2A §7.3 MUST support historyLength parameter
- ✅ **test_tasks_get_nonexistent** - A2A §7.3 MUST return TaskNotFoundError

### test_tasks_cancel_method.py - Task Cancellation
- ✅ **test_tasks_cancel_valid** - A2A §7.4 MUST support tasks/cancel
- ✅ **test_tasks_cancel_nonexistent** - A2A §7.4 MUST return TaskNotFoundError
- ❌ **test_tasks_cancel_already_canceled** - Optional (idempotency is quality)

### test_state_transitions.py - Task State Management
- ✅ **test_task_history_length** - A2A §7.3 MUST support historyLength parameter
- ❌ **test_task_state_transitions** - Optional (state transition details are SHOULD)

### test_protocol_violations.py - JSON-RPC Protocol Enforcement
- ✅ **test_duplicate_request_ids** - JSON-RPC 2.0 requires unique request IDs
- ✅ **test_raw_invalid_json** - JSON-RPC 2.0 MUST reject malformed JSON

## Optional Capability-Based Tests (MUST work IF capability declared)

### test_streaming_methods.py - Streaming Capability
- 🔄 **test_tasks_resubscribe** - MANDATORY if capabilities.streaming = true
- 🔄 **test_tasks_resubscribe_nonexistent** - MANDATORY if capabilities.streaming = true
- 🔄 **test_message_stream_basic** - MANDATORY if capabilities.streaming = true

### test_push_notification_config_methods.py - Push Notifications Capability
- 🔄 **test_create_task_push_notification_config** - MANDATORY if capabilities.pushNotifications = true
- 🔄 **test_get_push_notification_config** - MANDATORY if capabilities.pushNotifications = true
- 🔄 **test_create_task_push_notification_config_nonexistent** - MANDATORY if declared
- 🔄 **test_get_push_notification_config_nonexistent** - MANDATORY if declared

### test_message_send_method.py - Modality-Based Tests
- 🔄 **test_message_send_valid_file_part** - MANDATORY if file modality declared
- 🔄 **test_message_send_valid_data_part** - MANDATORY if data modality declared

## Optional Quality Tests (SHOULD/Recommended)

### test_transport_security.py - Security Best Practices
- 📋 **test_sut_uses_https** - A2A §3.1 "production deployments MUST use HTTPS"
- 📋 **test_http_to_https_redirect** - A2A §3.1 SHOULD redirect HTTP to HTTPS
- 📋 **test_https_url_in_agent_card** - A2A §2.1 URLs SHOULD be HTTPS in production

### test_authentication.py - Authentication Quality
- 📋 **test_auth_schemes_available** - A2A §4.1 SHOULD provide auth schemes
- 📋 **test_invalid_authentication** - A2A §4.1 SHOULD return proper 401 responses

### test_concurrency.py - Implementation Quality
- 📋 **test_parallel_requests** - Quality: SHOULD handle concurrent requests
- 📋 **test_rapid_sequential_requests** - Quality: SHOULD handle rapid requests
- 📋 **test_concurrent_operations_same_task** - Quality: SHOULD handle task concurrency

### test_edge_cases.py - Robustness Quality
- 📋 **test_very_long_string** - Quality: SHOULD handle large inputs gracefully
- 📋 **test_empty_arrays** - Quality: SHOULD handle edge cases
- 📋 **test_null_optional_fields** - Quality: SHOULD handle nulls properly
- 📋 **test_unexpected_json_types** - Quality: SHOULD validate types
- 📋 **test_extra_fields** - Quality: SHOULD handle unknown fields
- 📋 **test_unicode_and_special_chars** - Quality: SHOULD handle Unicode
- 📋 **test_boundary_values** - Quality: SHOULD handle boundary conditions

### test_resilience.py - Advanced Quality
- 📋 **test_streaming_reconnection_simulation** - Quality: SHOULD handle reconnection
- 📋 **test_partial_update_recovery** - Quality: SHOULD recover from partial failures

## SDK-Specific Tests (Being Removed/Fixed)

### test_sdk_limitations.py - Converted to Spec Compliance
- ✅ **test_history_length_parameter_compliance** - A2A §7.3 MUST support historyLength (previously SDK-specific)

## Utility/Helper Tests (Not Compliance Tests)

### test_agent_card_utils.py - Test Infrastructure
- 🔧 **test_fetch_agent_card_success** - Test utility
- 🔧 **test_fetch_agent_card_not_found** - Test utility  
- 🔧 **test_fetch_agent_card_invalid_json** - Test utility
- 🔧 **test_get_sut_rpc_endpoint** - Test utility
- 🔧 **test_get_capability_streaming** - Test utility
- 🔧 **test_get_capability_push_notifications** - Test utility
- 🔧 **test_get_supported_modalities** - Test utility
- 🔧 **test_get_authentication_schemes** - Test utility

### test_reference_task_ids.py - Protocol Utilities
- 🔧 **test_reference_task_ids_valid** - Test utility for reference handling
- 🔧 **test_reference_task_ids_invalid** - Test utility for reference validation

### test_invalid_business_logic.py - Error Handling Quality
- 📋 **test_unsupported_part_kind** - Quality: SHOULD reject invalid part types
- 📋 **test_invalid_file_part** - Quality: SHOULD validate file parts
- 📋 **test_very_large_message** - Quality: SHOULD handle size limits
- 📋 **test_empty_message_parts** - Quality: SHOULD validate message structure

## Summary

### Mandatory Categories:
- **✅ JSON-RPC 2.0 Compliance** (4 tests) - Hard requirement for any JSON-RPC server
- **✅ Agent Card Mandatory Fields** (3 tests) - Required by A2A specification
- **✅ Core Message Protocol** (4 tests) - SendMessage basic functionality
- **✅ Task Management Protocol** (5 tests) - tasks/get, tasks/cancel core functionality
- **✅ Protocol Violations** (2 tests) - Protocol compliance enforcement

**Total Mandatory: 18 tests** - These MUST pass for A2A compliance

### Conditional Mandatory Categories:
- **🔄 Capability-Based Tests** (8 tests) - MANDATORY if capability is declared, SKIP if not

### Optional Categories:
- **📋 Security Best Practices** (3 tests) - Production deployment quality
- **📋 Implementation Quality** (15 tests) - Robustness and performance
- **🔧 Test Infrastructure** (11 tests) - Testing utilities, not compliance

**Total: 69 tests analyzed**

## Classification Legend:
- ✅ **MANDATORY** - Must pass for A2A compliance (specification MUST/SHALL)
- 🔄 **CONDITIONAL MANDATORY** - Must pass IF capability is declared
- 📋 **OPTIONAL QUALITY** - Should pass for production quality (specification SHOULD)
- 🔧 **UTILITY** - Test infrastructure, not compliance validation 