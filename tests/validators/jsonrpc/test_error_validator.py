"""Tests for the JSON-RPC error validator."""

import pytest

from tck.validators.jsonrpc.error_validator import (
    JSONRPC_ERROR_CODES,
    ERROR_CODE_NAMES,
    ErrorValidationResult,
    get_error_code,
    get_error_name,
    validate_jsonrpc_error,
)


class TestErrorValidationResult:
    """Tests for the ErrorValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ErrorValidationResult(
            valid=True,
            expected_code=-32001,
            actual_code=-32001,
            message="Error code matches",
        )
        assert result.valid is True
        assert result.expected_code == -32001
        assert result.actual_code == -32001
        assert "matches" in result.message

    def test_invalid_result(self):
        """Test creating an invalid result."""
        result = ErrorValidationResult(
            valid=False,
            expected_code=-32001,
            actual_code=-32002,
            message="Error code mismatch",
        )
        assert result.valid is False
        assert result.expected_code == -32001
        assert result.actual_code == -32002

    def test_missing_actual_code(self):
        """Test result with missing actual code."""
        result = ErrorValidationResult(
            valid=False,
            expected_code=-32001,
            actual_code=None,
            message="No error field",
        )
        assert result.actual_code is None


class TestJSONRPCErrorCodes:
    """Tests for the JSONRPC_ERROR_CODES constant."""

    def test_contains_task_not_found(self):
        """Test TaskNotFoundError is defined."""
        assert "TaskNotFoundError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["TaskNotFoundError"] == -32001

    def test_contains_task_not_cancelable(self):
        """Test TaskNotCancelableError is defined."""
        assert "TaskNotCancelableError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["TaskNotCancelableError"] == -32002

    def test_contains_push_notification_not_supported(self):
        """Test PushNotificationNotSupportedError is defined."""
        assert "PushNotificationNotSupportedError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["PushNotificationNotSupportedError"] == -32003

    def test_contains_unsupported_operation(self):
        """Test UnsupportedOperationError is defined."""
        assert "UnsupportedOperationError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["UnsupportedOperationError"] == -32004

    def test_contains_content_type_not_supported(self):
        """Test ContentTypeNotSupportedError is defined."""
        assert "ContentTypeNotSupportedError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["ContentTypeNotSupportedError"] == -32005

    def test_contains_invalid_agent_response(self):
        """Test InvalidAgentResponseError is defined."""
        assert "InvalidAgentResponseError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InvalidAgentResponseError"] == -32006

    def test_contains_version_not_supported(self):
        """Test VersionNotSupportedError is defined."""
        assert "VersionNotSupportedError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["VersionNotSupportedError"] == -32009

    def test_contains_invalid_request(self):
        """Test InvalidRequestError is defined."""
        assert "InvalidRequestError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InvalidRequestError"] == -32600

    def test_contains_method_not_found(self):
        """Test MethodNotFoundError is defined."""
        assert "MethodNotFoundError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["MethodNotFoundError"] == -32601

    def test_contains_invalid_params(self):
        """Test InvalidParamsError is defined."""
        assert "InvalidParamsError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InvalidParamsError"] == -32602

    def test_contains_internal_error(self):
        """Test InternalError is defined."""
        assert "InternalError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InternalError"] == -32603

    def test_reverse_mapping_complete(self):
        """Test that ERROR_CODE_NAMES has all codes."""
        for name, code in JSONRPC_ERROR_CODES.items():
            assert code in ERROR_CODE_NAMES
            assert ERROR_CODE_NAMES[code] == name


class TestValidateJSONRPCError:
    """Tests for the validate_jsonrpc_error function."""

    def test_valid_error_match(self):
        """Test that matching error code returns valid=True."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32001, "message": "Task not found"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.expected_code == -32001
        assert result.actual_code == -32001

    def test_error_code_mismatch(self):
        """Test that mismatching error code returns valid=False."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32002, "message": "Task not cancelable"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.expected_code == -32001
        assert result.actual_code == -32002
        assert "mismatch" in result.message.lower()

    def test_missing_error_field(self):
        """Test handling of missing 'error' field."""
        response = {"jsonrpc": "2.0", "id": 1, "result": {"id": "task-123"}}
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_code is None
        assert "error" in result.message.lower()

    def test_error_not_object(self):
        """Test handling of non-object error field."""
        response = {"jsonrpc": "2.0", "id": 1, "error": "Something went wrong"}
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_code is None
        assert "not an object" in result.message.lower()

    def test_missing_code_field(self):
        """Test handling of missing 'code' field in error."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"message": "Task not found"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_code is None
        assert "code" in result.message.lower()

    def test_code_not_integer(self):
        """Test handling of non-integer error code."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": "-32001", "message": "Task not found"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_code is None
        assert "integer" in result.message.lower()

    def test_unknown_error_type(self):
        """Test handling of unknown expected error type."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32001, "message": "Task not found"},
        }
        result = validate_jsonrpc_error(response, "NonExistentError")
        assert result.valid is False
        assert "Unknown error type" in result.message

    def test_all_error_types(self):
        """Test that all defined error types can be validated."""
        for error_name, error_code in JSONRPC_ERROR_CODES.items():
            response = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": error_code, "message": f"Error: {error_name}"},
            }
            result = validate_jsonrpc_error(response, error_name)
            assert result.valid is True, f"Failed for {error_name}"
            assert result.expected_code == error_code
            assert result.actual_code == error_code

    def test_error_message_includes_details(self):
        """Test that error messages include helpful details."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32002, "message": "Cannot cancel"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        # Should mention both expected and actual
        assert "TaskNotFoundError" in result.message
        assert "-32001" in result.message
        assert "TaskNotCancelableError" in result.message
        assert "-32002" in result.message


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_error_name_known(self):
        """Test getting error name for known code."""
        assert get_error_name(-32001) == "TaskNotFoundError"
        assert get_error_name(-32600) == "InvalidRequestError"

    def test_get_error_name_unknown(self):
        """Test getting error name for unknown code."""
        assert get_error_name(-99999) is None

    def test_get_error_code_known(self):
        """Test getting error code for known name."""
        assert get_error_code("TaskNotFoundError") == -32001
        assert get_error_code("InternalError") == -32603

    def test_get_error_code_unknown(self):
        """Test getting error code for unknown name."""
        assert get_error_code("NonExistentError") is None
