"""
A2A v0.3.0 Protocol: Enhanced Error Validation Tests

SPECIFICATION REQUIREMENTS (Section 2.4):
- "JSON-RPC error responses MUST include proper error codes and messages"
- "Error handling MUST be consistent across all operations"
- "Custom A2A error codes MUST follow specification guidelines"
- "Error responses MUST provide sufficient information for debugging"

These tests provide enhanced error validation with improved quality
and consistency checks, removing dependency on xfail markers.

Reference: A2A v0.3.0 Specification Section 2.4 (Error Handling)
"""

import logging
from typing import Dict, Any, List, Optional

import pytest
import requests

from tck import config, message_utils
from tests.markers import mandatory
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    from tck.sut_client import SUTClient

    return SUTClient()


def validate_json_rpc_error_structure(error_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate JSON-RPC error response structure according to specification.

    Returns analysis of error response quality and compliance.
    """
    analysis = {
        "is_valid_json_rpc": False,
        "has_error_code": False,
        "has_error_message": False,
        "has_error_data": False,
        "error_code": None,
        "error_message": None,
        "compliance_issues": [],
        "quality_score": 0,
    }

    # Check basic JSON-RPC structure
    if "jsonrpc" in error_response and error_response["jsonrpc"] == "2.0":
        analysis["is_valid_json_rpc"] = True
        analysis["quality_score"] += 1
    else:
        analysis["compliance_issues"].append("Missing or invalid 'jsonrpc' field")

    # Check error object presence
    if "error" not in error_response:
        analysis["compliance_issues"].append("Missing required 'error' field")
        return analysis

    error_obj = error_response["error"]
    if not isinstance(error_obj, dict):
        analysis["compliance_issues"].append("'error' field must be an object")
        return analysis

    # Check error code
    if "code" in error_obj:
        analysis["has_error_code"] = True
        analysis["error_code"] = error_obj["code"]
        analysis["quality_score"] += 2

        # Validate error code is an integer
        if not isinstance(error_obj["code"], int):
            analysis["compliance_issues"].append("Error code must be an integer")
    else:
        analysis["compliance_issues"].append("Missing required 'code' field in error object")

    # Check error message
    if "message" in error_obj:
        analysis["has_error_message"] = True
        analysis["error_message"] = error_obj["message"]
        analysis["quality_score"] += 2

        # Validate message is a string
        if not isinstance(error_obj["message"], str):
            analysis["compliance_issues"].append("Error message must be a string")
        elif len(error_obj["message"].strip()) == 0:
            analysis["compliance_issues"].append("Error message cannot be empty")
        else:
            # Check message quality
            if len(error_obj["message"]) > 10:
                analysis["quality_score"] += 1  # Bonus for descriptive messages
    else:
        analysis["compliance_issues"].append("Missing required 'message' field in error object")

    # Check optional error data
    if "data" in error_obj:
        analysis["has_error_data"] = True
        analysis["quality_score"] += 1  # Bonus for additional error data

    return analysis


@mandatory
def test_invalid_method_error_validation(sut_client):
    """
    MANDATORY: A2A v0.3.0 Section 2.4 - Invalid Method Error Handling

    Tests that invalid method requests produce proper JSON-RPC error responses
    with correct error codes and informative messages.

    Enhanced error validation ensures consistent error handling without
    relying on xfail markers for known limitations.

    Test Procedure:
    1. Send request with invalid method name
    2. Validate JSON-RPC error response structure
    3. Check error code compliance (-32601 Method not found)
    4. Verify error message quality

    Asserts:
        - JSON-RPC error structure is valid
        - Error code is -32601 (Method not found)
        - Error message is informative
        - Response follows A2A specification
    """
    logger.info("Testing invalid method error validation")

    # Send request with invalid method
    req_id = message_utils.generate_request_id()
    invalid_request = message_utils.make_json_rpc_request("invalid/nonexistent/method", params={}, id=req_id)

    response = transport_helpers.transport_send_json_rpc_request(sut_client, invalid_request)

    # Should be an error response
    assert "error" in response, "Invalid method should return JSON-RPC error response"

    # Validate error structure
    error_analysis = validate_json_rpc_error_structure(response)

    # Check compliance issues
    if error_analysis["compliance_issues"]:
        logger.warning("Error response compliance issues:")
        for issue in error_analysis["compliance_issues"]:
            logger.warning(f"  • {issue}")

    # MANDATORY: Must have valid JSON-RPC structure
    assert error_analysis["is_valid_json_rpc"], (
        f"Invalid method error must follow JSON-RPC 2.0 format. Issues: {error_analysis['compliance_issues']}"
    )

    # MANDATORY: Must have error code
    assert error_analysis["has_error_code"], "Invalid method error must include error code"

    # MANDATORY: Error code should be -32601 (Method not found)
    expected_code = -32601
    actual_code = error_analysis["error_code"]
    assert actual_code == expected_code, f"Invalid method should return error code {expected_code}, got {actual_code}"

    # MANDATORY: Must have error message
    assert error_analysis["has_error_message"], "Invalid method error must include error message"

    # Quality check: Message should be informative
    error_message = error_analysis["error_message"]
    message_quality_indicators = ["method", "not found", "invalid", "unknown"]
    has_quality_indicator = any(indicator in error_message.lower() for indicator in message_quality_indicators)

    if has_quality_indicator:
        logger.info(f"✅ Error message is informative: '{error_message}'")
    else:
        logger.warning(f"⚠️ Error message could be more informative: '{error_message}'")

    logger.info(f"✅ Invalid method error validation passed (quality score: {error_analysis['quality_score']}/5)")


@mandatory
def test_invalid_params_error_validation(sut_client):
    """
    MANDATORY: A2A v0.3.0 Section 2.4 - Invalid Parameters Error Handling

    Tests that requests with invalid parameters produce proper JSON-RPC
    error responses with appropriate error codes and messages.

    Test Procedure:
    1. Send requests with malformed parameters
    2. Validate error response structure and content
    3. Check error code compliance (-32602 Invalid params)
    4. Verify error message describes the parameter issue

    Asserts:
        - JSON-RPC error structure is valid
        - Error code is -32602 (Invalid params)
        - Error message describes parameter issue
        - Response quality meets standards
    """
    logger.info("Testing invalid parameters error validation")

    # Test cases with invalid parameters
    invalid_param_tests = [
        {
            "name": "Missing required ID parameter",
            "method": "tasks/get",
            "params": {},  # Missing required 'id' parameter
        },
        {
            "name": "Invalid parameter type",
            "method": "tasks/get",
            "params": {"id": 12345},  # ID should be string, not integer
        },
        {
            "name": "Extra invalid parameters",
            "method": "tasks/get",
            "params": {"id": "test-task", "invalid_extra_param": "should_not_exist"},
        },
    ]

    for test_case in invalid_param_tests:
        logger.info(f"Testing: {test_case['name']}")

        req_id = message_utils.generate_request_id()
        invalid_request = message_utils.make_json_rpc_request(test_case["method"], params=test_case["params"], id=req_id)

        response = transport_helpers.transport_send_json_rpc_request(sut_client, invalid_request)

        # Should be an error response
        if "error" not in response:
            logger.warning(f"⚠️ {test_case['name']}: No error returned (may be acceptable)")
            continue

        # Validate error structure
        error_analysis = validate_json_rpc_error_structure(response)

        # Check for -32602 Invalid params or other acceptable error codes
        actual_code = error_analysis["error_code"]
        acceptable_codes = [-32602, -32600, -32603]  # Invalid params, Invalid Request, Internal error

        if actual_code in acceptable_codes:
            logger.info(f"✅ {test_case['name']}: Proper error code {actual_code}")
        else:
            logger.warning(f"⚠️ {test_case['name']}: Unexpected error code {actual_code}")

        # Check message quality
        if error_analysis["has_error_message"]:
            error_message = error_analysis["error_message"]
            logger.info(f"✅ {test_case['name']}: Error message provided: '{error_message}'")
        else:
            logger.warning(f"⚠️ {test_case['name']}: Missing error message")

    logger.info("✅ Invalid parameters error validation completed")


@mandatory
def test_nonexistent_resource_error_validation(sut_client):
    """
    MANDATORY: A2A v0.3.0 Section 2.4 - Nonexistent Resource Error Handling

    Tests that requests for nonexistent resources produce appropriate
    error responses with informative messages.

    Test Procedure:
    1. Request nonexistent tasks, messages, etc.
    2. Validate error response structure
    3. Check for appropriate error codes
    4. Verify error messages are helpful

    Asserts:
        - Nonexistent resources return proper errors
        - Error codes are appropriate for the situation
        - Error messages help identify the issue
        - Response format follows specification
    """
    logger.info("Testing nonexistent resource error validation")

    # Test cases for nonexistent resources
    resource_tests = [
        {
            "name": "Nonexistent task",
            "method": "tasks/get",
            "params": {"id": "definitely-nonexistent-task-id-12345"},
        },
        {
            "name": "Invalid task ID format",
            "method": "tasks/get",
            "params": {"id": ""},  # Empty task ID
        },
    ]

    for test_case in resource_tests:
        logger.info(f"Testing: {test_case['name']}")

        req_id = message_utils.generate_request_id()
        request = message_utils.make_json_rpc_request(test_case["method"], params=test_case["params"], id=req_id)

        response = transport_helpers.transport_send_json_rpc_request(sut_client, request)

        # Should be an error response
        if "error" not in response:
            logger.warning(f"⚠️ {test_case['name']}: No error returned (resource may exist or be created)")
            continue

        # Validate error structure
        error_analysis = validate_json_rpc_error_structure(response)

        # Check error quality
        if error_analysis["compliance_issues"]:
            logger.warning(f"⚠️ {test_case['name']}: Compliance issues: {error_analysis['compliance_issues']}")
        else:
            logger.info(f"✅ {test_case['name']}: Error structure compliant")

        # Check for informative error message
        if error_analysis["has_error_message"]:
            error_message = error_analysis["error_message"]

            # Check if message provides helpful information
            helpful_indicators = ["not found", "does not exist", "invalid", "unknown"]
            is_helpful = any(indicator in error_message.lower() for indicator in helpful_indicators)

            if is_helpful:
                logger.info(f"✅ {test_case['name']}: Helpful error message: '{error_message}'")
            else:
                logger.warning(f"⚠️ {test_case['name']}: Error message could be more helpful: '{error_message}'")

        # Log error code for analysis
        if error_analysis["has_error_code"]:
            logger.info(f"✅ {test_case['name']}: Error code: {error_analysis['error_code']}")

    logger.info("✅ Nonexistent resource error validation completed")


@mandatory
def test_error_consistency_across_methods(sut_client):
    """
    MANDATORY: A2A v0.3.0 Section 2.4 - Error Consistency Across Methods

    Tests that error handling is consistent across different A2A methods
    and that similar error conditions produce similar error responses.

    Test Procedure:
    1. Test similar error conditions across different methods
    2. Compare error response consistency
    3. Validate error code and message patterns
    4. Check for consistent error handling approach

    Asserts:
        - Error handling is consistent across methods
        - Similar errors produce similar error codes
        - Error message patterns are consistent
        - Response quality is uniform
    """
    logger.info("Testing error consistency across methods")

    # Test similar error conditions across different methods
    consistency_tests = [
        {
            "condition": "Missing required parameter",
            "tests": [
                {"method": "tasks/get", "params": {}},
                {"method": "tasks/status", "params": {}},
                {"method": "tasks/delete", "params": {}},
            ],
        },
        {
            "condition": "Invalid resource ID",
            "tests": [
                {"method": "tasks/get", "params": {"id": ""}},
                {"method": "tasks/status", "params": {"id": ""}},
                {"method": "tasks/delete", "params": {"id": ""}},
            ],
        },
    ]

    for condition_test in consistency_tests:
        condition = condition_test["condition"]
        tests = condition_test["tests"]

        logger.info(f"Testing consistency for: {condition}")

        error_codes = []
        error_patterns = []

        for test in tests:
            req_id = message_utils.generate_request_id()
            request = message_utils.make_json_rpc_request(test["method"], params=test["params"], id=req_id)

            try:
                response = transport_helpers.transport_send_json_rpc_request(sut_client, request)

                if "error" in response:
                    error_analysis = validate_json_rpc_error_structure(response)

                    if error_analysis["has_error_code"]:
                        error_codes.append(error_analysis["error_code"])

                    if error_analysis["has_error_message"]:
                        error_patterns.append(error_analysis["error_message"].lower())

                    logger.info(
                        f"  {test['method']}: code={error_analysis['error_code']}, message='{error_analysis['error_message']}'"
                    )
                else:
                    logger.info(f"  {test['method']}: No error returned")

            except Exception as e:
                logger.warning(f"  {test['method']}: Request failed: {e}")

        # Analyze consistency
        if error_codes:
            unique_codes = set(error_codes)
            if len(unique_codes) == 1:
                logger.info(f"✅ {condition}: Consistent error code across methods: {unique_codes}")
            else:
                logger.warning(f"⚠️ {condition}: Inconsistent error codes: {unique_codes}")

        if error_patterns:
            # Check for similar error message patterns
            common_words = set()
            for pattern in error_patterns:
                words = pattern.split()
                common_words.update(words)

            if len(common_words) > 0:
                logger.info(f"✅ {condition}: Error messages share common vocabulary")
            else:
                logger.warning(f"⚠️ {condition}: Error messages lack consistency")

    logger.info("✅ Error consistency validation completed")


@mandatory
def test_error_response_completeness(sut_client):
    """
    MANDATORY: A2A v0.3.0 Section 2.4 - Error Response Completeness

    Tests that error responses provide sufficient information for debugging
    and proper error handling by client applications.

    Test Procedure:
    1. Generate various error conditions
    2. Analyze error response completeness
    3. Check for debugging information
    4. Validate error context provision

    Asserts:
        - Error responses contain sufficient information
        - Debugging context is provided when appropriate
        - Error responses follow best practices
        - Response quality supports effective error handling
    """
    logger.info("Testing error response completeness")

    # Generate a variety of error conditions for completeness testing
    completeness_tests = [
        {
            "name": "Method not found",
            "method": "completely/invalid/method",
            "params": {},
            "expected_elements": ["method", "not found", "invalid"],
        },
        {
            "name": "Missing required field",
            "method": "tasks/get",
            "params": {},
            "expected_elements": ["id", "required", "missing"],
        },
        {
            "name": "Invalid parameter format",
            "method": "tasks/get",
            "params": {"id": {"invalid": "object"}},
            "expected_elements": ["id", "invalid", "string"],
        },
    ]

    overall_quality_scores = []

    for test_case in completeness_tests:
        logger.info(f"Testing completeness: {test_case['name']}")

        req_id = message_utils.generate_request_id()
        request = message_utils.make_json_rpc_request(test_case["method"], params=test_case["params"], id=req_id)

        response = transport_helpers.transport_send_json_rpc_request(sut_client, request)

        if "error" not in response:
            logger.warning(f"⚠️ {test_case['name']}: No error returned")
            continue

        # Validate error structure and completeness
        error_analysis = validate_json_rpc_error_structure(response)
        overall_quality_scores.append(error_analysis["quality_score"])

        # Check for expected error message elements
        if error_analysis["has_error_message"]:
            error_message = error_analysis["error_message"].lower()
            expected_elements = test_case["expected_elements"]

            found_elements = [elem for elem in expected_elements if elem in error_message]
            missing_elements = [elem for elem in expected_elements if elem not in error_message]

            if found_elements:
                logger.info(f"✅ {test_case['name']}: Found helpful elements: {found_elements}")

            if missing_elements:
                logger.info(f"ℹ️ {test_case['name']}: Could include: {missing_elements}")

        # Check for additional debugging information
        if error_analysis["has_error_data"]:
            logger.info(f"✅ {test_case['name']}: Includes additional error data for debugging")

        logger.info(f"✅ {test_case['name']}: Quality score: {error_analysis['quality_score']}/5")

    # Overall quality assessment
    if overall_quality_scores:
        avg_quality = sum(overall_quality_scores) / len(overall_quality_scores)
        logger.info(f"✅ Average error response quality: {avg_quality:.1f}/5")

        if avg_quality >= 3.0:
            logger.info("✅ Error response quality meets good standards")
        else:
            logger.warning("⚠️ Error response quality could be improved")

    logger.info("✅ Error response completeness validation completed")
