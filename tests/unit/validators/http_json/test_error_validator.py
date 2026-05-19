"""Tests for the HTTP+JSON error validator."""

from __future__ import annotations

from http import HTTPStatus

import pytest

from tck.validators.http_json.error_validator import (
    HTTP_JSON_ERROR_STATUS,
    STATUS_TO_ERRORS,
    AIP193Error,
    ErrorValidationResult,
    get_expected_status,
    get_possible_errors,
    validate_http_json_error,
)


HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND
HTTP_BAD_REQUEST = HTTPStatus.BAD_REQUEST
HTTP_CONFLICT = HTTPStatus.CONFLICT
HTTP_UNSUPPORTED_MEDIA_TYPE = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
HTTP_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR


class TestAIP193Error:
    """Tests for the AIP193Error dataclass."""

    def test_create_with_required_fields(self) -> None:
        """Test creating AIP193Error with required fields."""
        err = AIP193Error(code=HTTP_NOT_FOUND)
        assert err.code == HTTP_NOT_FOUND
        assert err.status == ""
        assert err.message == ""
        assert err.details == []

    def test_create_with_all_fields(self) -> None:
        """Test creating AIP193Error with all fields."""
        err = AIP193Error(
            code=HTTP_NOT_FOUND,
            status="NOT_FOUND",
            message="Task with ID 'xyz' was not found",
            details=[{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "TASK_NOT_FOUND", "domain": "a2a-protocol.org"}],
        )
        assert err.status == "NOT_FOUND"
        assert err.message == "Task with ID 'xyz' was not found"
        assert len(err.details) == 1

    def test_from_dict_valid(self) -> None:
        """Test creating from dict with valid AIP-193 structure."""
        data = {
            "error": {
                "code": HTTP_NOT_FOUND,
                "status": "NOT_FOUND",
                "message": "Not found",
            },
        }
        err = AIP193Error.from_dict(data)
        assert err.code == HTTP_NOT_FOUND
        assert err.status == "NOT_FOUND"
        assert err.message == "Not found"

    def test_from_dict_with_details(self) -> None:
        """Test creating from dict with details array."""
        data = {
            "error": {
                "code": HTTP_NOT_FOUND,
                "status": "NOT_FOUND",
                "message": "Task not found",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": "TASK_NOT_FOUND",
                        "domain": "a2a-protocol.org",
                    },
                ],
            },
        }
        err = AIP193Error.from_dict(data)
        assert len(err.details) == 1
        assert err.details[0]["reason"] == "TASK_NOT_FOUND"

    def test_from_dict_missing_error(self) -> None:
        """Test that missing error field raises ValueError."""
        data = {"code": HTTP_NOT_FOUND}
        with pytest.raises(ValueError, match="error"):
            AIP193Error.from_dict(data)

    def test_from_dict_missing_code(self) -> None:
        """Test that missing code raises ValueError."""
        data = {"error": {"status": "NOT_FOUND"}}
        with pytest.raises(ValueError, match="code"):
            AIP193Error.from_dict(data)

    def test_from_dict_error_not_object(self) -> None:
        """Test that non-object error field raises ValueError."""
        data = {"error": "not an object"}
        with pytest.raises(ValueError, match="object"):
            AIP193Error.from_dict(data)


class TestErrorValidationResult:
    """Tests for the ErrorValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ErrorValidationResult(
            valid=True,
            expected_status=HTTP_NOT_FOUND,
            actual_status=HTTP_NOT_FOUND,
            aip193_error=None,
            message="Status code matches",
        )
        assert result.valid is True
        assert result.expected_status == HTTP_NOT_FOUND
        assert result.actual_status == HTTP_NOT_FOUND

    def test_result_with_aip193_error(self) -> None:
        """Test result with AIP-193 error."""
        err = AIP193Error(code=HTTP_NOT_FOUND, status="NOT_FOUND")
        result = ErrorValidationResult(
            valid=True,
            expected_status=HTTP_NOT_FOUND,
            actual_status=HTTP_NOT_FOUND,
            aip193_error=err,
            message="Status code matches",
        )
        assert result.aip193_error is not None
        assert result.aip193_error.code == HTTP_NOT_FOUND

    def test_result_with_missing_status(self) -> None:
        """Test result with missing actual status."""
        result = ErrorValidationResult(
            valid=False,
            expected_status=HTTP_NOT_FOUND,
            actual_status=None,
            aip193_error=None,
            message="No status code",
        )
        assert result.actual_status is None


class TestHTTPJSONErrorStatus:
    """Tests for the HTTP_JSON_ERROR_STATUS constant."""

    def test_contains_task_not_found(self) -> None:
        """Test TaskNotFoundError maps to 404."""
        assert "TaskNotFoundError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["TaskNotFoundError"] == HTTP_NOT_FOUND

    def test_contains_task_not_cancelable(self) -> None:
        """Test TaskNotCancelableError maps to 409."""
        assert "TaskNotCancelableError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["TaskNotCancelableError"] == HTTP_CONFLICT

    def test_contains_content_type_not_supported(self) -> None:
        """Test ContentTypeNotSupportedError maps to 415."""
        assert "ContentTypeNotSupportedError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["ContentTypeNotSupportedError"] == HTTP_UNSUPPORTED_MEDIA_TYPE

    def test_contains_internal_error(self) -> None:
        """Test InternalError maps to 500."""
        assert "InternalError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["InternalError"] == HTTP_INTERNAL_SERVER_ERROR

    def test_contains_invalid_request(self) -> None:
        """Test InvalidRequestError maps to 400."""
        assert "InvalidRequestError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["InvalidRequestError"] == HTTP_BAD_REQUEST

    def test_contains_unsupported_operation(self) -> None:
        """Test UnsupportedOperationError maps to 400."""
        assert "UnsupportedOperationError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["UnsupportedOperationError"] == HTTP_BAD_REQUEST

    def test_contains_version_not_supported(self) -> None:
        """Test VersionNotSupportedError maps to 400."""
        assert "VersionNotSupportedError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["VersionNotSupportedError"] == HTTP_BAD_REQUEST

    def test_reverse_mapping_exists(self) -> None:
        """Test that STATUS_TO_ERRORS is populated."""
        assert HTTP_NOT_FOUND in STATUS_TO_ERRORS
        assert "TaskNotFoundError" in STATUS_TO_ERRORS[HTTP_NOT_FOUND]


class TestValidateHTTPJSONError:
    """Tests for the validate_http_json_error function."""

    def test_valid_status_match_dict(self) -> None:
        """Test matching status code with dict response."""
        response = {
            "status_code": HTTP_NOT_FOUND,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.expected_status == HTTP_NOT_FOUND
        assert result.actual_status == HTTP_NOT_FOUND

    def test_status_mismatch(self) -> None:
        """Test mismatching status code."""
        response = {
            "status_code": HTTP_INTERNAL_SERVER_ERROR,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.expected_status == HTTP_NOT_FOUND
        assert result.actual_status == HTTP_INTERNAL_SERVER_ERROR
        assert "mismatch" in result.message.lower()

    def test_missing_status_code(self) -> None:
        """Test handling of missing status code."""
        response = {
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_status is None
        assert "status code" in result.message.lower()

    def test_unknown_error_type(self) -> None:
        """Test handling of unknown expected error type."""
        response = {
            "status_code": HTTP_NOT_FOUND,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "NonExistentError")
        assert result.valid is False
        assert "Unknown error type" in result.message

    def test_aip193_error_parsed(self) -> None:
        """Test that AIP-193 error is parsed from response body."""
        response = {
            "status_code": HTTP_NOT_FOUND,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "error": {
                    "code": HTTP_NOT_FOUND,
                    "status": "NOT_FOUND",
                    "message": "Task 'xyz' does not exist",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "TASK_NOT_FOUND",
                            "domain": "a2a-protocol.org",
                        },
                    ],
                },
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.aip193_error is not None
        assert result.aip193_error.code == HTTP_NOT_FOUND
        assert result.aip193_error.status == "NOT_FOUND"
        assert result.aip193_error.message == "Task 'xyz' does not exist"
        assert len(result.aip193_error.details) == 1

    def test_aip193_error_not_parsed_without_error_key(self) -> None:
        """Test that AIP-193 error is not parsed when body has no 'error' key."""
        response = {
            "status_code": HTTP_NOT_FOUND,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "code": HTTP_NOT_FOUND,
                "message": "Not found",
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.aip193_error is None

    def test_invalid_aip193_error(self) -> None:
        """Test handling of invalid AIP-193 error structure."""
        response = {
            "status_code": HTTP_NOT_FOUND,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "error": "not an object",
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert "Invalid AIP-193 error" in result.message

    def test_all_error_types(self) -> None:
        """Test that all defined error types can be validated."""
        for error_name, status_code in HTTP_JSON_ERROR_STATUS.items():
            response = {
                "status_code": status_code,
                "headers": {},
                "body": None,
            }
            result = validate_http_json_error(response, error_name)
            assert result.valid is True, f"Failed for {error_name}"
            assert result.expected_status == status_code
            assert result.actual_status == status_code

    def test_error_message_includes_details(self) -> None:
        """Test that error messages include helpful details."""
        response = {
            "status_code": HTTP_INTERNAL_SERVER_ERROR,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert "TaskNotFoundError" in result.message
        assert "404" in result.message
        assert "500" in result.message


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_expected_status_known(self) -> None:
        """Test getting expected status for known error."""
        assert get_expected_status("TaskNotFoundError") == HTTP_NOT_FOUND
        assert get_expected_status("InternalError") == HTTP_INTERNAL_SERVER_ERROR

    def test_get_expected_status_unknown(self) -> None:
        """Test getting expected status for unknown error."""
        assert get_expected_status("NonExistentError") is None

    def test_get_possible_errors_known(self) -> None:
        """Test getting possible errors for known status."""
        errors = get_possible_errors(HTTP_NOT_FOUND)
        assert "TaskNotFoundError" in errors

    def test_get_possible_errors_unknown(self) -> None:
        """Test getting possible errors for unknown status."""
        errors = get_possible_errors(999)
        assert errors == []

    def test_get_possible_errors_multiple(self) -> None:
        """Test that 400 maps to multiple possible errors."""
        errors = get_possible_errors(HTTP_BAD_REQUEST)
        assert len(errors) > 1
        assert "InvalidRequestError" in errors

    def test_get_possible_errors_conflict(self) -> None:
        """Test that 409 maps to TaskNotCancelableError."""
        errors = get_possible_errors(HTTP_CONFLICT)
        assert "TaskNotCancelableError" in errors
