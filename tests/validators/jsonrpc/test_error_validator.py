"""Tests for the JSON-RPC error validator."""


from tck.validators.jsonrpc.error_validator import (
    ERROR_CODE_NAMES,
    JSONRPC_ERROR_CODES,
    ErrorValidationResult,
    get_error_code,
    get_error_name,
    validate_jsonrpc_error,
)


TASK_NOT_FOUND = JSONRPC_ERROR_CODES["TaskNotFoundError"]
TASK_NOT_CANCELABLE = JSONRPC_ERROR_CODES["TaskNotCancelableError"]
PUSH_NOT_SUPPORTED = JSONRPC_ERROR_CODES["PushNotificationNotSupportedError"]
UNSUPPORTED_OPERATION = JSONRPC_ERROR_CODES["UnsupportedOperationError"]
CONTENT_TYPE_NOT_SUPPORTED = JSONRPC_ERROR_CODES["ContentTypeNotSupportedError"]
INVALID_AGENT_RESPONSE = JSONRPC_ERROR_CODES["InvalidAgentResponseError"]
VERSION_NOT_SUPPORTED = JSONRPC_ERROR_CODES["VersionNotSupportedError"]
INVALID_REQUEST = JSONRPC_ERROR_CODES["InvalidRequestError"]
METHOD_NOT_FOUND = JSONRPC_ERROR_CODES["MethodNotFoundError"]
INVALID_PARAMS = JSONRPC_ERROR_CODES["InvalidParamsError"]
INTERNAL_ERROR = JSONRPC_ERROR_CODES["InternalError"]


class TestErrorValidationResult:
    """Tests for the ErrorValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ErrorValidationResult(
            valid=True,
            expected_code=TASK_NOT_FOUND,
            actual_code=TASK_NOT_FOUND,
            message="Error code matches",
        )
        assert result.valid is True
        assert result.expected_code == TASK_NOT_FOUND
        assert result.actual_code == TASK_NOT_FOUND
        assert "matches" in result.message

    def test_invalid_result(self) -> None:
        """Test creating an invalid result."""
        result = ErrorValidationResult(
            valid=False,
            expected_code=TASK_NOT_FOUND,
            actual_code=TASK_NOT_CANCELABLE,
            message="Error code mismatch",
        )
        assert result.valid is False
        assert result.expected_code == TASK_NOT_FOUND
        assert result.actual_code == TASK_NOT_CANCELABLE

    def test_missing_actual_code(self) -> None:
        """Test result with missing actual code."""
        result = ErrorValidationResult(
            valid=False,
            expected_code=TASK_NOT_FOUND,
            actual_code=None,
            message="No error field",
        )
        assert result.actual_code is None


class TestJSONRPCErrorCodes:
    """Tests for the JSONRPC_ERROR_CODES constant."""

    def test_contains_task_not_found(self) -> None:
        """Test TaskNotFoundError is defined."""
        assert "TaskNotFoundError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["TaskNotFoundError"] == TASK_NOT_FOUND

    def test_contains_task_not_cancelable(self) -> None:
        """Test TaskNotCancelableError is defined."""
        assert "TaskNotCancelableError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["TaskNotCancelableError"] == TASK_NOT_CANCELABLE

    def test_contains_push_notification_not_supported(self) -> None:
        """Test PushNotificationNotSupportedError is defined."""
        assert "PushNotificationNotSupportedError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["PushNotificationNotSupportedError"] == PUSH_NOT_SUPPORTED

    def test_contains_unsupported_operation(self) -> None:
        """Test UnsupportedOperationError is defined."""
        assert "UnsupportedOperationError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["UnsupportedOperationError"] == UNSUPPORTED_OPERATION

    def test_contains_content_type_not_supported(self) -> None:
        """Test ContentTypeNotSupportedError is defined."""
        assert "ContentTypeNotSupportedError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["ContentTypeNotSupportedError"] == CONTENT_TYPE_NOT_SUPPORTED

    def test_contains_invalid_agent_response(self) -> None:
        """Test InvalidAgentResponseError is defined."""
        assert "InvalidAgentResponseError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InvalidAgentResponseError"] == INVALID_AGENT_RESPONSE

    def test_contains_version_not_supported(self) -> None:
        """Test VersionNotSupportedError is defined."""
        assert "VersionNotSupportedError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["VersionNotSupportedError"] == VERSION_NOT_SUPPORTED

    def test_contains_invalid_request(self) -> None:
        """Test InvalidRequestError is defined."""
        assert "InvalidRequestError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InvalidRequestError"] == INVALID_REQUEST

    def test_contains_method_not_found(self) -> None:
        """Test MethodNotFoundError is defined."""
        assert "MethodNotFoundError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["MethodNotFoundError"] == METHOD_NOT_FOUND

    def test_contains_invalid_params(self) -> None:
        """Test InvalidParamsError is defined."""
        assert "InvalidParamsError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InvalidParamsError"] == INVALID_PARAMS

    def test_contains_internal_error(self) -> None:
        """Test InternalError is defined."""
        assert "InternalError" in JSONRPC_ERROR_CODES
        assert JSONRPC_ERROR_CODES["InternalError"] == INTERNAL_ERROR

    def test_reverse_mapping_complete(self) -> None:
        """Test that ERROR_CODE_NAMES has all codes."""
        for name, code in JSONRPC_ERROR_CODES.items():
            assert code in ERROR_CODE_NAMES
            assert ERROR_CODE_NAMES[code] == name


class TestValidateJSONRPCError:
    """Tests for the validate_jsonrpc_error function."""

    def test_valid_error_match(self) -> None:
        """Test that matching error code returns valid=True."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": TASK_NOT_FOUND, "message": "Task not found"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.expected_code == TASK_NOT_FOUND
        assert result.actual_code == TASK_NOT_FOUND

    def test_error_code_mismatch(self) -> None:
        """Test that mismatching error code returns valid=False."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": TASK_NOT_CANCELABLE, "message": "Task not cancelable"},
        }
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.expected_code == TASK_NOT_FOUND
        assert result.actual_code == TASK_NOT_CANCELABLE
        assert "mismatch" in result.message.lower()

    def test_missing_error_field(self) -> None:
        """Test handling of missing 'error' field."""
        response = {"jsonrpc": "2.0", "id": 1, "result": {"id": "task-123"}}
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_code is None
        assert "error" in result.message.lower()

    def test_error_not_object(self) -> None:
        """Test handling of non-object error field."""
        response = {"jsonrpc": "2.0", "id": 1, "error": "Something went wrong"}
        result = validate_jsonrpc_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_code is None
        assert "not an object" in result.message.lower()

    def test_missing_code_field(self) -> None:
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

    def test_code_not_integer(self) -> None:
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

    def test_unknown_error_type(self) -> None:
        """Test handling of unknown expected error type."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": TASK_NOT_FOUND, "message": "Task not found"},
        }
        result = validate_jsonrpc_error(response, "NonExistentError")
        assert result.valid is False
        assert "Unknown error type" in result.message

    def test_all_error_types(self) -> None:
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

    def test_error_message_includes_details(self) -> None:
        """Test that error messages include helpful details."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": TASK_NOT_CANCELABLE, "message": "Cannot cancel"},
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

    def test_get_error_name_known(self) -> None:
        """Test getting error name for known code."""
        assert get_error_name(TASK_NOT_FOUND) == "TaskNotFoundError"
        assert get_error_name(INVALID_REQUEST) == "InvalidRequestError"

    def test_get_error_name_unknown(self) -> None:
        """Test getting error name for unknown code."""
        assert get_error_name(-99999) is None

    def test_get_error_code_known(self) -> None:
        """Test getting error code for known name."""
        assert get_error_code("TaskNotFoundError") == TASK_NOT_FOUND
        assert get_error_code("InternalError") == INTERNAL_ERROR

    def test_get_error_code_unknown(self) -> None:
        """Test getting error code for unknown name."""
        assert get_error_code("NonExistentError") is None
