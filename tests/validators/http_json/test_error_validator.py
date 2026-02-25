"""Tests for the HTTP+JSON error validator."""

import pytest

from tck.validators.http_json.error_validator import (
    HTTP_JSON_ERROR_STATUS,
    STATUS_TO_ERRORS,
    ErrorValidationResult,
    ProblemDetails,
    get_expected_status,
    get_possible_errors,
    validate_http_json_error,
)


class TestProblemDetails:
    """Tests for the ProblemDetails dataclass."""

    def test_create_with_required_fields(self):
        """Test creating ProblemDetails with required fields."""
        pd = ProblemDetails(
            type="https://example.com/errors/not-found",
            title="Not Found",
            status=404,
        )
        assert pd.type == "https://example.com/errors/not-found"
        assert pd.title == "Not Found"
        assert pd.status == 404
        assert pd.detail == ""
        assert pd.instance == ""

    def test_create_with_all_fields(self):
        """Test creating ProblemDetails with all fields."""
        pd = ProblemDetails(
            type="https://example.com/errors/not-found",
            title="Not Found",
            status=404,
            detail="Task with ID 'xyz' was not found",
            instance="/tasks/xyz",
        )
        assert pd.detail == "Task with ID 'xyz' was not found"
        assert pd.instance == "/tasks/xyz"

    def test_from_dict_required_fields(self):
        """Test creating from dict with required fields."""
        data = {
            "type": "https://example.com/errors/not-found",
            "title": "Not Found",
            "status": 404,
        }
        pd = ProblemDetails.from_dict(data)
        assert pd.type == "https://example.com/errors/not-found"
        assert pd.title == "Not Found"
        assert pd.status == 404

    def test_from_dict_all_fields(self):
        """Test creating from dict with all fields."""
        data = {
            "type": "https://example.com/errors/not-found",
            "title": "Not Found",
            "status": 404,
            "detail": "Task not found",
            "instance": "/tasks/123",
        }
        pd = ProblemDetails.from_dict(data)
        assert pd.detail == "Task not found"
        assert pd.instance == "/tasks/123"

    def test_from_dict_missing_type(self):
        """Test that missing type raises ValueError."""
        data = {"title": "Not Found", "status": 404}
        with pytest.raises(ValueError, match="type"):
            ProblemDetails.from_dict(data)

    def test_from_dict_missing_title(self):
        """Test that missing title raises ValueError."""
        data = {"type": "https://example.com/errors/not-found", "status": 404}
        with pytest.raises(ValueError, match="title"):
            ProblemDetails.from_dict(data)

    def test_from_dict_missing_status(self):
        """Test that missing status raises ValueError."""
        data = {
            "type": "https://example.com/errors/not-found",
            "title": "Not Found",
        }
        with pytest.raises(ValueError, match="status"):
            ProblemDetails.from_dict(data)


class TestErrorValidationResult:
    """Tests for the ErrorValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ErrorValidationResult(
            valid=True,
            expected_status=404,
            actual_status=404,
            problem_details=None,
            message="Status code matches",
        )
        assert result.valid is True
        assert result.expected_status == 404
        assert result.actual_status == 404

    def test_result_with_problem_details(self):
        """Test result with problem details."""
        pd = ProblemDetails(
            type="https://example.com/errors/not-found",
            title="Not Found",
            status=404,
        )
        result = ErrorValidationResult(
            valid=True,
            expected_status=404,
            actual_status=404,
            problem_details=pd,
            message="Status code matches",
        )
        assert result.problem_details is not None
        assert result.problem_details.status == 404

    def test_result_with_missing_status(self):
        """Test result with missing actual status."""
        result = ErrorValidationResult(
            valid=False,
            expected_status=404,
            actual_status=None,
            problem_details=None,
            message="No status code",
        )
        assert result.actual_status is None


class TestHTTPJSONErrorStatus:
    """Tests for the HTTP_JSON_ERROR_STATUS constant."""

    def test_contains_task_not_found(self):
        """Test TaskNotFoundError maps to 404."""
        assert "TaskNotFoundError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["TaskNotFoundError"] == 404

    def test_contains_task_not_cancelable(self):
        """Test TaskNotCancelableError maps to 400."""
        assert "TaskNotCancelableError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["TaskNotCancelableError"] == 400

    def test_contains_content_type_not_supported(self):
        """Test ContentTypeNotSupportedError maps to 415."""
        assert "ContentTypeNotSupportedError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["ContentTypeNotSupportedError"] == 415

    def test_contains_internal_error(self):
        """Test InternalError maps to 500."""
        assert "InternalError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["InternalError"] == 500

    def test_contains_invalid_request(self):
        """Test InvalidRequestError maps to 400."""
        assert "InvalidRequestError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["InvalidRequestError"] == 400

    def test_contains_unsupported_operation(self):
        """Test UnsupportedOperationError maps to 400."""
        assert "UnsupportedOperationError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["UnsupportedOperationError"] == 400

    def test_contains_version_not_supported(self):
        """Test VersionNotSupportedError maps to 400."""
        assert "VersionNotSupportedError" in HTTP_JSON_ERROR_STATUS
        assert HTTP_JSON_ERROR_STATUS["VersionNotSupportedError"] == 400

    def test_reverse_mapping_exists(self):
        """Test that STATUS_TO_ERRORS is populated."""
        assert 404 in STATUS_TO_ERRORS
        assert "TaskNotFoundError" in STATUS_TO_ERRORS[404]


class TestValidateHTTPJSONError:
    """Tests for the validate_http_json_error function."""

    def test_valid_status_match_dict(self):
        """Test matching status code with dict response."""
        response = {
            "status_code": 404,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.expected_status == 404
        assert result.actual_status == 404

    def test_status_mismatch(self):
        """Test mismatching status code."""
        response = {
            "status_code": 500,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.expected_status == 404
        assert result.actual_status == 500
        assert "mismatch" in result.message.lower()

    def test_missing_status_code(self):
        """Test handling of missing status code."""
        response = {
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert result.actual_status is None
        assert "status code" in result.message.lower()

    def test_unknown_error_type(self):
        """Test handling of unknown expected error type."""
        response = {
            "status_code": 404,
            "headers": {},
            "body": None,
        }
        result = validate_http_json_error(response, "NonExistentError")
        assert result.valid is False
        assert "Unknown error type" in result.message

    def test_problem_details_parsed(self):
        """Test that Problem Details are parsed when content type matches."""
        response = {
            "status_code": 404,
            "headers": {"Content-Type": "application/problem+json"},
            "body": {
                "type": "https://example.com/errors/task-not-found",
                "title": "Task Not Found",
                "status": 404,
                "detail": "Task 'xyz' does not exist",
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.problem_details is not None
        assert result.problem_details.type == "https://example.com/errors/task-not-found"
        assert result.problem_details.title == "Task Not Found"
        assert result.problem_details.status == 404
        assert result.problem_details.detail == "Task 'xyz' does not exist"

    def test_problem_details_case_insensitive_header(self):
        """Test that Content-Type header is case-insensitive."""
        response = {
            "status_code": 404,
            "headers": {"content-type": "application/problem+json"},
            "body": {
                "type": "https://example.com/errors/not-found",
                "title": "Not Found",
                "status": 404,
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.problem_details is not None

    def test_problem_details_not_parsed_for_json(self):
        """Test that Problem Details are not parsed for regular JSON."""
        response = {
            "status_code": 404,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "type": "https://example.com/errors/not-found",
                "title": "Not Found",
                "status": 404,
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is True
        assert result.problem_details is None

    def test_invalid_problem_details(self):
        """Test handling of invalid Problem Details."""
        response = {
            "status_code": 404,
            "headers": {"Content-Type": "application/problem+json"},
            "body": {
                "title": "Not Found",
                # Missing required 'type' field
            },
        }
        result = validate_http_json_error(response, "TaskNotFoundError")
        assert result.valid is False
        assert "Invalid Problem Details" in result.message

    def test_all_error_types(self):
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

    def test_error_message_includes_details(self):
        """Test that error messages include helpful details."""
        response = {
            "status_code": 500,
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

    def test_get_expected_status_known(self):
        """Test getting expected status for known error."""
        assert get_expected_status("TaskNotFoundError") == 404
        assert get_expected_status("InternalError") == 500

    def test_get_expected_status_unknown(self):
        """Test getting expected status for unknown error."""
        assert get_expected_status("NonExistentError") is None

    def test_get_possible_errors_known(self):
        """Test getting possible errors for known status."""
        errors = get_possible_errors(404)
        assert "TaskNotFoundError" in errors

    def test_get_possible_errors_unknown(self):
        """Test getting possible errors for unknown status."""
        errors = get_possible_errors(999)
        assert errors == []

    def test_get_possible_errors_multiple(self):
        """Test that 400 maps to multiple possible errors."""
        errors = get_possible_errors(400)
        assert len(errors) > 1
        assert "InvalidRequestError" in errors
        assert "TaskNotCancelableError" in errors
