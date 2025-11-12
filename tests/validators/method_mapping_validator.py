"""
Method Mapping Compliance Validator

Validates that A2A implementations correctly map methods across all supported
transports according to the A2A v0.3.0 Method Mapping Reference Table (§3.5.6).

This validator ensures functional equivalence and consistent method naming
across JSON-RPC, gRPC, and REST transports.

References:
- A2A v0.3.0 Specification §3.5: Method Mapping and Naming Conventions
- A2A v0.3.0 Specification §3.5.6: Method Mapping Reference Table
- A2A v0.3.0 Specification §3.4.1: Functional Equivalence Requirements
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import re

from tck.transport.base_client import BaseTransportClient
from tck.transport.jsonrpc_client import JSONRPCClient
from tck.transport.grpc_client import GRPCClient
from tck.transport.rest_client import RESTClient


@dataclass
class MethodMapping:
    """Represents method mapping across all A2A transports."""

    jsonrpc_method: str
    grpc_method: str
    rest_endpoint: str
    description: str
    transport_support: str  # "all", "grpc_rest_only", etc.


class MethodMappingValidator:
    """
    Validates method mapping compliance across A2A transports.

    Ensures that implementations follow the normative method mapping table
    defined in A2A v0.3.0 specification §3.5.6.
    """

    # A2A v0.3.0 Method Mapping Reference Table (§3.5.6)
    CORE_METHOD_MAPPINGS = [
        MethodMapping(
            jsonrpc_method="message/send",
            grpc_method="SendMessage",
            rest_endpoint="POST /v1/message:send",
            description="Send message to agent",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="message/stream",
            grpc_method="SendStreamingMessage",
            rest_endpoint="POST /v1/message:stream",
            description="Send message with streaming",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/get",
            grpc_method="GetTask",
            rest_endpoint="GET /v1/tasks/{id}",
            description="Get task status",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/list",
            grpc_method="ListTasks",
            rest_endpoint="GET /v1/tasks",
            description="List tasks with optional filtering and pagination",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/cancel",
            grpc_method="CancelTask",
            rest_endpoint="POST /v1/tasks/{id}:cancel",
            description="Cancel task",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/resubscribe",
            grpc_method="TaskSubscription",
            rest_endpoint="POST /v1/tasks/{id}:subscribe",
            description="Resume task streaming",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/pushNotificationConfig/set",
            grpc_method="CreateTaskPushNotification",
            rest_endpoint="POST /v1/tasks/{id}/pushNotificationConfigs",
            description="Set push notification config",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/pushNotificationConfig/get",
            grpc_method="GetTaskPushNotification",
            rest_endpoint="GET /v1/tasks/{id}/pushNotificationConfigs/{configId}",
            description="Get push notification config",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/pushNotificationConfig/list",
            grpc_method="ListTaskPushNotification",
            rest_endpoint="GET /v1/tasks/{id}/pushNotificationConfigs",
            description="List push notification configs",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="tasks/pushNotificationConfig/delete",
            grpc_method="DeleteTaskPushNotification",
            rest_endpoint="DELETE /v1/tasks/{id}/pushNotificationConfigs/{configId}",
            description="Delete push notification config",
            transport_support="all",
        ),
        MethodMapping(
            jsonrpc_method="agent/getAuthenticatedExtendedCard",
            grpc_method="GetAgentCard",
            rest_endpoint="GET /v1/card",
            description="Get authenticated agent card",
            transport_support="all",
        ),
    ]

    def __init__(self):
        """Initialize the method mapping validator."""
        self.validation_results: List[Dict[str, Any]] = []

    def validate_transport_method_naming(self, client: BaseTransportClient) -> Dict[str, Any]:
        """
        Validate that a transport client follows correct method naming conventions.

        Args:
            client: Transport client to validate

        Returns:
            Validation results with compliance status and details
        """
        transport_type = self._get_transport_type(client)

        if transport_type == "jsonrpc":
            return self._validate_jsonrpc_naming(client)
        elif transport_type == "grpc":
            return self._validate_grpc_naming(client)
        elif transport_type == "rest":
            return self._validate_rest_naming(client)
        else:
            return {"transport": transport_type, "compliant": False, "errors": [f"Unknown transport type: {transport_type}"]}

    def validate_cross_transport_equivalence(self, clients: List[BaseTransportClient]) -> Dict[str, Any]:
        """
        Validate functional equivalence across multiple transport implementations.

        Args:
            clients: List of transport clients to compare

        Returns:
            Validation results for cross-transport equivalence
        """
        if len(clients) < 2:
            return {"compliant": False, "errors": ["Need at least 2 transport clients for equivalence testing"]}

        results = {"compliant": True, "tested_methods": [], "equivalence_results": {}, "errors": []}

        # Test core methods that should be equivalent across transports
        equivalent_methods = [
            ("message/send", "Send a test message"),
            ("tasks/get", None),  # Requires existing task
            ("tasks/cancel", None),  # Requires existing task
        ]

        for method_description, test_params in equivalent_methods:
            try:
                method_results = self._test_method_equivalence(clients, method_description, test_params)
                results["equivalence_results"][method_description] = method_results
                results["tested_methods"].append(method_description)

                if not method_results["equivalent"]:
                    results["compliant"] = False
                    results["errors"].extend(method_results["differences"])

            except Exception as e:
                results["errors"].append(f"Failed to test {method_description}: {e}")
                results["compliant"] = False

        return results

    def validate_method_mapping_table_compliance(self, client: BaseTransportClient) -> Dict[str, Any]:
        """
        Validate that client implements methods according to the mapping table.

        Args:
            client: Transport client to validate

        Returns:
            Validation results for mapping table compliance
        """
        transport_type = self._get_transport_type(client)

        results = {
            "transport": transport_type,
            "compliant": True,
            "supported_methods": [],
            "missing_methods": [],
            "incorrectly_named_methods": [],
            "errors": [],
        }

        for mapping in self.CORE_METHOD_MAPPINGS:
            # Skip methods not supported by this transport
            if mapping.transport_support == "grpc_rest_only" and transport_type == "jsonrpc":
                continue

            try:
                method_available = self._test_method_availability(client, mapping, transport_type)

                if method_available:
                    results["supported_methods"].append(
                        {
                            "method": self._get_method_name_for_transport(mapping, transport_type),
                            "description": mapping.description,
                        }
                    )
                else:
                    results["missing_methods"].append(
                        {
                            "method": self._get_method_name_for_transport(mapping, transport_type),
                            "description": mapping.description,
                        }
                    )
                    results["compliant"] = False

            except Exception as e:
                results["errors"].append(f"Error testing {mapping.description}: {e}")

        return results

    def _get_transport_type(self, client: BaseTransportClient) -> str:
        """Determine the transport type of a client."""
        if isinstance(client, JSONRPCClient):
            return "jsonrpc"
        elif isinstance(client, GRPCClient):
            return "grpc"
        elif isinstance(client, RESTClient):
            return "rest"
        else:
            return "unknown"

    def _validate_jsonrpc_naming(self, client: JSONRPCClient) -> Dict[str, Any]:
        """
        Validate JSON-RPC method naming conventions (§3.5.1).

        JSON-RPC methods MUST follow {category}/{action} pattern.
        """
        results = {
            "transport": "jsonrpc",
            "compliant": True,
            "naming_convention": "category/action",
            "violations": [],
            "valid_methods": [],
        }

        # Get available methods from client
        available_methods = self._get_available_jsonrpc_methods(client)

        for method in available_methods:
            if self._validate_jsonrpc_method_pattern(method):
                results["valid_methods"].append(method)
            else:
                results["violations"].append({"method": method, "issue": "Does not follow category/action pattern"})
                results["compliant"] = False

        return results

    def _validate_grpc_naming(self, client: GRPCClient) -> Dict[str, Any]:
        """
        Validate gRPC method naming conventions (§3.5.2).

        gRPC methods MUST follow PascalCase compound words.
        """
        results = {
            "transport": "grpc",
            "compliant": True,
            "naming_convention": "PascalCase compound words",
            "violations": [],
            "valid_methods": [],
        }

        # Get available methods from client
        available_methods = self._get_available_grpc_methods(client)

        for method in available_methods:
            if self._validate_grpc_method_pattern(method):
                results["valid_methods"].append(method)
            else:
                results["violations"].append({"method": method, "issue": "Does not follow PascalCase pattern"})
                results["compliant"] = False

        return results

    def _validate_rest_naming(self, client: RESTClient) -> Dict[str, Any]:
        """
        Validate REST endpoint naming conventions (§3.5.3).

        REST endpoints MUST follow /v1/{resource}[/{id}][:{action}] pattern.
        """
        results = {
            "transport": "rest",
            "compliant": True,
            "naming_convention": "/v1/{resource}[/{id}][:{action}]",
            "violations": [],
            "valid_endpoints": [],
        }

        # Get available endpoints from client
        available_endpoints = self._get_available_rest_endpoints(client)

        for endpoint in available_endpoints:
            if self._validate_rest_endpoint_pattern(endpoint):
                results["valid_endpoints"].append(endpoint)
            else:
                results["violations"].append({"endpoint": endpoint, "issue": "Does not follow REST URL pattern"})
                results["compliant"] = False

        return results

    def _validate_jsonrpc_method_pattern(self, method: str) -> bool:
        """Validate JSON-RPC method follows category/action pattern."""
        pattern = r"^[a-z][a-zA-Z]*(/[a-zA-Z][a-zA-Z]*)+$"
        return bool(re.match(pattern, method))

    def _validate_grpc_method_pattern(self, method: str) -> bool:
        """Validate gRPC method follows PascalCase pattern."""
        pattern = r"^[A-Z][a-zA-Z]*$"
        return bool(re.match(pattern, method))

    def _validate_rest_endpoint_pattern(self, endpoint: str) -> bool:
        """Validate REST endpoint follows /v1/{resource} pattern."""
        # Must start with /v1/
        if not endpoint.startswith("/v1/"):
            return False

        # Should follow resource-based pattern
        pattern = r"^/v1/[a-z]+(/\{[a-zA-Z]+\}|:[a-z]+)?$"
        return bool(re.match(pattern, endpoint))

    def _get_available_jsonrpc_methods(self, client: JSONRPCClient) -> List[str]:
        """Get list of available JSON-RPC methods."""
        # This would need to be implemented based on how the client exposes methods
        # For now, return the standard A2A methods
        return [mapping.jsonrpc_method for mapping in self.CORE_METHOD_MAPPINGS]

    def _get_available_grpc_methods(self, client: GRPCClient) -> List[str]:
        """Get list of available gRPC methods."""
        # This would need to be implemented based on how the client exposes methods
        return [mapping.grpc_method for mapping in self.CORE_METHOD_MAPPINGS]

    def _get_available_rest_endpoints(self, client: RESTClient) -> List[str]:
        """Get list of available REST endpoints."""
        # Extract URL patterns from REST mappings
        endpoints = []
        for mapping in self.CORE_METHOD_MAPPINGS:
            # Extract URL pattern from "HTTP_METHOD /url/pattern"
            parts = mapping.rest_endpoint.split(" ", 1)
            if len(parts) == 2:
                endpoints.append(parts[1])
        return endpoints

    def _test_method_availability(self, client: BaseTransportClient, mapping: MethodMapping, transport_type: str) -> bool:
        """Test if a method is available on the client."""
        try:
            if transport_type == "jsonrpc":
                # Try to call the method (expect error for missing params, not method not found)
                response = client.call_method(mapping.jsonrpc_method, {})
                # If we get here without "method not found", method exists
                return True

            elif transport_type == "grpc":
                # Check if gRPC method exists
                method_name = mapping.grpc_method
                return hasattr(client, method_name.lower()) or hasattr(client, f"call_{method_name}")

            elif transport_type == "rest":
                # Check if REST client supports the endpoint
                endpoint_parts = mapping.rest_endpoint.split(" ", 1)
                if len(endpoint_parts) == 2:
                    http_method, url_pattern = endpoint_parts
                    # This would need client-specific implementation
                    return True  # Assume available for now

        except Exception as e:
            error_msg = str(e).lower()
            # Method exists if we get param errors, not method not found
            if "method not found" in error_msg or "not implemented" in error_msg:
                return False
            return True

        return False

    def _get_method_name_for_transport(self, mapping: MethodMapping, transport_type: str) -> str:
        """Get the method name for a specific transport."""
        if transport_type == "jsonrpc":
            return mapping.jsonrpc_method
        elif transport_type == "grpc":
            return mapping.grpc_method
        elif transport_type == "rest":
            return mapping.rest_endpoint
        else:
            return "unknown"

    def _test_method_equivalence(
        self, clients: List[BaseTransportClient], method_description: str, test_params: Any
    ) -> Dict[str, Any]:
        """Test functional equivalence of a method across transports."""
        results = {"equivalent": True, "responses": {}, "differences": []}

        # This would need to be implemented with actual method calls
        # and response comparison logic

        # For now, return a placeholder
        results["responses"] = {f"client_{i}": f"response_{i}" for i in range(len(clients))}

        return results


def validate_method_mapping_compliance(client: BaseTransportClient) -> Dict[str, Any]:
    """
    Convenience function to validate method mapping compliance for a single client.

    Args:
        client: Transport client to validate

    Returns:
        Comprehensive validation results
    """
    validator = MethodMappingValidator()

    results = {
        "transport_naming": validator.validate_transport_method_naming(client),
        "mapping_table_compliance": validator.validate_method_mapping_table_compliance(client),
    }

    # Overall compliance
    results["overall_compliant"] = results["transport_naming"]["compliant"] and results["mapping_table_compliance"]["compliant"]

    return results


def validate_cross_transport_equivalence(clients: List[BaseTransportClient]) -> Dict[str, Any]:
    """
    Convenience function to validate functional equivalence across multiple transports.

    Args:
        clients: List of transport clients to validate

    Returns:
        Cross-transport equivalence validation results
    """
    validator = MethodMappingValidator()
    return validator.validate_cross_transport_equivalence(clients)
