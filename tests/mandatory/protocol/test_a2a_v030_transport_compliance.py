"""
A2A v0.3.0 Transport Compliance Tests

This module contains mandatory tests for validating A2A v0.3.0 transport compliance
requirements. These tests ensure that transport implementations conform to the
multi-transport architecture defined in the A2A v0.3.0 specification.

Specification Reference: A2A Protocol v0.3.0 §3 - Transport and Format
"""

import logging
import pytest
from typing import Dict, Any

from tests.validators.a2a_v030_compliance import (
    TransportComplianceValidator,
    MethodMappingValidator,
    validate_a2a_v030_compliance,
)
from tests.markers import mandatory_protocol
from tck.transport.base_client import TransportType

logger = logging.getLogger(__name__)


@mandatory_protocol
def test_transport_compliance_validation(sut_client):
    """
    MANDATORY: A2A v0.3.0 §3.2 - Transport Protocol Compliance

    The A2A v0.3.0 specification requires that each implemented transport
    protocol MUST conform to its specific requirements (JSON-RPC, gRPC, or REST).
    This test validates that the primary transport client meets all compliance
    requirements for its transport type.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §3.2.1, §3.2.2, §3.2.3
    """
    # Validate the primary transport client compliance
    validation_result = TransportComplianceValidator.validate_transport_compliance(sut_client)

    # Log validation details for debugging
    logger.info(f"Transport compliance validation for {validation_result['transport_type']}")
    logger.info(f"Required methods: {validation_result['required_methods']}")
    logger.info(f"Optional methods: {validation_result['optional_methods']}")
    logger.info(f"Transport features: {validation_result['transport_specific_features']}")

    # Check for compliance issues
    if not validation_result["compliant"]:
        issues = "\n".join(validation_result["issues"])
        pytest.fail(f"Transport compliance validation failed for {validation_result['transport_type']}:\n{issues}")

    # Verify required methods are present
    assert len(validation_result["required_methods"]) > 0, "Transport must define required methods"

    # Verify no critical issues
    assert len(validation_result["issues"]) == 0, f"Transport compliance issues found: {validation_result['issues']}"


@mandatory_protocol
def test_required_method_availability(sut_client):
    """
    MANDATORY: A2A v0.3.0 §3.2 - Required Method Implementation

    The A2A v0.3.0 specification requires that each transport implement
    a set of core methods. This test validates that all required methods
    are available on the transport client.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §3.5.6 - Method Mapping Reference Table
    """
    validation_result = TransportComplianceValidator.validate_transport_compliance(sut_client)
    transport_type = sut_client.transport_type

    # Check each required method is actually available
    for method_name in validation_result["required_methods"]:
        assert hasattr(sut_client, method_name), (
            f"Required method '{method_name}' missing from {transport_type.value} transport client"
        )

        # Verify method is callable
        method = getattr(sut_client, method_name)
        assert callable(method), f"Required method '{method_name}' is not callable in {transport_type.value} transport client"


@mandatory_protocol
def test_transport_specific_features(sut_client):
    """
    MANDATORY: A2A v0.3.0 §3.2 - Transport-Specific Feature Support

    The A2A v0.3.0 specification defines transport-specific features that
    MUST be supported when implementing each transport protocol. This test
    validates that transport-specific features are properly implemented.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §3.2.1, §3.2.2, §3.2.3
    """
    validation_result = TransportComplianceValidator.validate_transport_compliance(sut_client)
    transport_type = sut_client.transport_type

    # Verify transport-specific features are declared
    features = validation_result["transport_specific_features"]
    assert len(features) > 0, f"Transport {transport_type.value} must declare transport-specific features"

    # Validate transport-specific requirements
    if transport_type == TransportType.JSON_RPC:
        assert "sse_streaming" in features, "JSON-RPC transport must support Server-Sent Events streaming"
        assert "json_rpc_error_codes" in features, "JSON-RPC transport must support standard JSON-RPC error codes"

    elif transport_type == TransportType.GRPC:
        assert "protobuf_serialization" in features, "gRPC transport must support Protocol Buffers serialization"
        assert "grpc_streaming" in features, "gRPC transport must support gRPC server streaming"
        # Verify gRPC-specific method
        assert hasattr(sut_client, "list_tasks"), "gRPC transport must implement list_tasks method"

    elif transport_type == TransportType.REST:
        assert "http_status_codes" in features, "REST transport must support proper HTTP status codes"
        assert "rest_url_patterns" in features, "REST transport must support RESTful URL patterns"
        # Verify REST-specific method
        assert hasattr(sut_client, "list_tasks"), "REST transport must implement list_tasks method"


@mandatory_protocol
def test_multi_transport_method_mapping(all_transport_clients):
    """
    MANDATORY: A2A v0.3.0 §3.5 - Method Mapping Compliance

    The A2A v0.3.0 specification requires consistent method mapping across
    all supported transports. When multiple transports are available, they
    MUST provide equivalent functionality through properly mapped methods.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §3.5.4 - Method Mapping Compliance
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Multi-transport method mapping requires 2+ transports")

    # Validate method mapping across all available transports
    validation_result = MethodMappingValidator.validate_method_mapping(all_transport_clients)

    # Log method mapping details
    logger.info(f"Method mapping validation across {len(all_transport_clients)} transports")
    for method, coverage in validation_result["method_coverage"].items():
        logger.info(f"Method '{method}': available in {coverage['available_transports']}")
        if coverage["missing_transports"]:
            logger.warning(f"Method '{method}': missing in {coverage['missing_transports']}")

    # Check for method mapping compliance
    if not validation_result["compliant"]:
        issues = "\n".join(validation_result["issues"])
        pytest.fail(f"Method mapping validation failed:\n{issues}")

    # Verify each transport has required methods according to its type
    for transport_type, client in all_transport_clients.items():
        transport_validation = TransportComplianceValidator.validate_transport_compliance(client)

        assert transport_validation["compliant"], (
            f"Transport {transport_type.value} failed individual compliance: {transport_validation['issues']}"
        )


@mandatory_protocol
def test_comprehensive_a2a_v030_compliance(all_transport_clients):
    """
    MANDATORY: A2A v0.3.0 - Comprehensive Multi-Transport Compliance

    The A2A v0.3.0 specification requires comprehensive compliance across
    all implemented transports, including transport compliance, method mapping,
    and functional equivalence. This test performs complete validation.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 - Complete Multi-Transport Architecture
    """
    # Perform comprehensive A2A v0.3.0 compliance validation
    validation_result = validate_a2a_v030_compliance(all_transport_clients)

    # Log comprehensive validation summary
    summary = validation_result["summary"]
    logger.info(f"A2A v0.3.0 Compliance Summary:")
    logger.info(f"  Transports tested: {summary['transports_tested']}")
    logger.info(f"  Compliant transports: {summary['compliant_transports']}")
    logger.info(f"  Method mapping compliant: {summary['method_mapping_compliant']}")
    logger.info(f"  Overall compliant: {validation_result['overall_compliant']}")

    # Check individual transport compliance
    for transport_name, transport_result in validation_result["transport_compliance"].items():
        logger.info(f"  {transport_name}: {'✓' if transport_result['compliant'] else '✗'}")
        if not transport_result["compliant"]:
            for issue in transport_result["issues"]:
                logger.error(f"    Issue: {issue}")

    # Fail if not compliant
    if not validation_result["overall_compliant"]:
        issues = "\n".join(validation_result["issues"])
        pytest.fail(f"A2A v0.3.0 compliance validation failed:\n{issues}")

    # Verify all transports are individually compliant
    assert summary["compliant_transports"] == summary["transports_tested"], (
        f"Not all transports are compliant: {summary['compliant_transports']}/{summary['transports_tested']}"
    )

    # Verify method mapping compliance (when applicable)
    if summary["transports_tested"] > 1:
        assert summary["method_mapping_compliant"], "Method mapping compliance failed for multi-transport implementation"

    # Verify overall compliance
    assert validation_result["overall_compliant"], "Overall A2A v0.3.0 compliance validation failed"
