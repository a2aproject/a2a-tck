"""JSON-RPC response validator for A2A protocol.

Validates the JSON-RPC 2.0 envelope structure and delegates payload
validation of the ``result`` field to the underlying JSONSchemaValidator.
"""

from __future__ import annotations

from typing import Any

from tck.validators.json_schema import JSONSchemaValidator, ValidationResult


class JsonRpcResponseValidator:
    """Validates JSON-RPC 2.0 responses wrapping A2A protocol objects.

    A valid JSON-RPC 2.0 success response looks like::

        {"jsonrpc": "2.0", "id": 1, "result": { ... }}

    This validator first checks the envelope, then extracts ``result``
    and delegates to a :class:`JSONSchemaValidator` for schema validation.
    """

    def __init__(self, schema_validator: JSONSchemaValidator) -> None:
        self._schema_validator = schema_validator

    def validate(
        self,
        response: dict[str, Any],
        schema_ref: str,
    ) -> ValidationResult:
        """Validate a JSON-RPC response against the envelope and a schema ref.

        Args:
            response: The full JSON-RPC response dict (``raw_response``).
            schema_ref: The A2A schema definition to validate the ``result``
                        against (e.g. ``"Task"``, ``"ListTasksResponse"``).

        Returns:
            A :class:`ValidationResult` with any envelope or schema errors.
        """
        errors: list[str] = []

        # --- Envelope checks ---
        if not isinstance(response, dict):
            return ValidationResult(
                valid=False,
                errors=["Response is not a JSON object"],
                schema_ref=schema_ref,
            )

        if response.get("jsonrpc") != "2.0":
            errors.append(
                f"$.jsonrpc: expected '2.0', got {response.get('jsonrpc')!r}"
            )

        if "id" not in response:
            errors.append("$.id: missing required field")

        # An error response should not be schema-validated
        if "error" in response:
            errors.append(
                f"$.error: JSON-RPC error response "
                f"(code={response['error'].get('code')}, "
                f"message={response['error'].get('message')!r})"
            )
            return ValidationResult(
                valid=False, errors=errors, schema_ref=schema_ref
            )

        if "result" not in response:
            errors.append("$.result: missing required field")
            return ValidationResult(
                valid=False, errors=errors, schema_ref=schema_ref
            )

        # If envelope itself has errors, report them before schema validation
        if errors:
            return ValidationResult(
                valid=False, errors=errors, schema_ref=schema_ref
            )

        # --- Delegate payload validation to JSONSchemaValidator ---
        return self._schema_validator.validate(response["result"], schema_ref)
