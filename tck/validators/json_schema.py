"""JSON Schema validator for A2A protocol responses.

This module provides validation of JSON responses against the A2A JSON Schema.
It supports reference resolution for the bundled a2a.json schema format.
"""

from __future__ import annotations

import json
import re

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from jsonschema.validators import validator_for


if TYPE_CHECKING:
    from pathlib import Path

    from jsonschema import ValidationError


@dataclass
class ValidationResult:
    """Result of a JSON Schema validation.

    Attributes:
        valid: True if the response passed validation.
        errors: List of error messages with JSON paths.
        schema_ref: The schema reference that was validated against.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    schema_ref: str = ""


class JSONSchemaValidator:
    """Validates JSON responses against the A2A JSON Schema.

    This validator loads the bundled a2a.json schema and validates responses
    against specific definitions within it. It handles the custom $ref format
    used in the schema (e.g., 'a2a.v1.Task.jsonschema.json').

    Example:
        >>> validator = JSONSchemaValidator(Path("specification/a2a.json"))
        >>> result = validator.validate({"id": "123", "status": {}}, "Task")
        >>> print(result.valid)
        True
    """

    def __init__(self, schema_path: Path) -> None:
        """Initialize the validator with a schema file.

        Args:
            schema_path: Path to the a2a.json schema file.

        Raises:
            FileNotFoundError: If the schema file does not exist.
            json.JSONDecodeError: If the schema file is not valid JSON.
        """
        self._schema_path = schema_path
        with schema_path.open() as f:
            self._schema = json.load(f)

        # Build a mapping from $ref values to definition names
        self._ref_to_definition = self._build_ref_mapping()

        # Pre-resolve the schema for validation
        self._resolved_schema = self._resolve_all_refs(self._schema)

    def _build_ref_mapping(self) -> dict[str, str]:
        """Build a mapping from external $ref values to definition names.

        The a2a.json schema uses external-looking $ref values like
        'a2a.v1.TaskStatus.jsonschema.json' that need to be resolved to
        internal definition names like 'Task Status'.

        Returns:
            A dict mapping $ref values to definition names.
        """
        mapping: dict[str, str] = {}
        definitions = self._schema.get("definitions", {})

        for def_name in definitions:
            # Convert definition name to possible $ref patterns
            # "Task Status" -> "TaskStatus" -> "lf.a2a.v1.TaskStatus.jsonschema.json"
            camel_name = def_name.replace(" ", "")
            ref_value = f"lf.a2a.v1.{camel_name}.jsonschema.json"
            mapping[ref_value] = def_name
            # Also support legacy prefix without "lf." for older schemas
            legacy_ref = f"a2a.v1.{camel_name}.jsonschema.json"
            mapping[legacy_ref] = def_name

            # Also handle google.protobuf types
            if def_name in ("Struct", "Timestamp", "Value"):
                google_ref = f"google.protobuf.{def_name}.jsonschema.json"
                mapping[google_ref] = def_name

        return mapping

    def _resolve_ref(self, ref_value: str, visited: set[str]) -> dict[str, Any] | None:
        """Resolve a single $ref value to its definition.

        Args:
            ref_value: The $ref value to resolve.
            visited: Set of visited definition names to prevent infinite recursion.

        Returns:
            The resolved definition, or None if not found or already visited.
        """
        def_name: str | None = None

        # Handle internal references (already in #/definitions/... format)
        if ref_value.startswith("#/definitions/"):
            def_name = ref_value[len("#/definitions/") :]
        # Handle external-looking references
        else:
            def_name = self._ref_to_definition.get(ref_value)

        if def_name is None:
            return None

        if def_name in visited:
            # Return a placeholder for recursive types
            return {"type": "object"}

        definition = self._schema.get("definitions", {}).get(def_name)
        if definition:
            new_visited = visited | {def_name}
            return self._resolve_all_refs(definition, new_visited)

        return None

    def _resolve_all_refs(self, obj: Any, visited: set[str] | None = None) -> Any:
        """Recursively resolve all $ref values in the schema.

        Args:
            obj: The JSON object to process.
            visited: Set of visited definition names to prevent infinite recursion.

        Returns:
            The object with all $refs resolved to their definitions.
        """
        if visited is None:
            visited = set()

        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_value = obj["$ref"]
                resolved = self._resolve_ref(ref_value, visited)

                if resolved is not None:
                    # If there are other properties, merge them (though typically
                    # in JSON Schema, $ref should be the only property)
                    if len(obj) > 1:
                        # Merge other properties into the resolved schema
                        result = dict(resolved)
                        for k, v in obj.items():
                            if k != "$ref":
                                result[k] = self._resolve_all_refs(v, visited)
                        return result
                    return resolved

                # Unknown reference - remove the $ref to prevent jsonschema
                # from trying to resolve it as an external URL
                if len(obj) == 1:
                    # If $ref is the only property, return an any-type schema
                    return {"type": "object", "additionalProperties": True}
                # Remove $ref and keep other properties
                return {
                    k: self._resolve_all_refs(v, visited)
                    for k, v in obj.items()
                    if k != "$ref"
                }

            # Process all keys in the dict
            return {k: self._resolve_all_refs(v, visited) for k, v in obj.items()}

        if isinstance(obj, list):
            return [self._resolve_all_refs(item, visited) for item in obj]

        return obj

    def _get_definition(self, schema_ref: str) -> dict[str, Any] | None:
        """Get a definition from the schema by reference.

        Args:
            schema_ref: Either a definition name (e.g., "Task") or a full reference
                       (e.g., "#/definitions/Task").

        Returns:
            The definition dict, or None if not found.
        """
        definitions = self._schema.get("definitions", {})

        # Handle full reference format
        if schema_ref.startswith("#/definitions/"):
            def_name = schema_ref[len("#/definitions/") :]
            return definitions.get(def_name)

        # Handle $defs format (some schemas use this)
        if schema_ref.startswith("#/$defs/"):
            def_name = schema_ref[len("#/$defs/") :]
            return definitions.get(def_name)

        # Handle direct definition name
        if schema_ref in definitions:
            return definitions[schema_ref]

        # Try to find by removing spaces from input (e.g., "TaskStatus" -> "Task Status")
        for def_name in definitions:
            if def_name.replace(" ", "") == schema_ref.replace(" ", ""):
                return definitions[def_name]

        return None

    def _format_json_path(self, path: list[str | int]) -> str:
        """Format a JSON path in JSONPath notation.

        Args:
            path: List of path elements (strings for object keys, ints for array indices).

        Returns:
            A string in JSONPath notation (e.g., '$.task.status').
        """
        if not path:
            return "$"

        result = "$"
        for element in path:
            if isinstance(element, int):
                result += f"[{element}]"
            # Use bracket notation for keys with special characters
            elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(element)):
                result += f".{element}"
            else:
                result += f"['{element}']"
        return result

    def _format_error(self, error: ValidationError) -> str:
        """Format a validation error with JSON path.

        Args:
            error: The validation error from jsonschema.

        Returns:
            A formatted error message including the JSON path.
        """
        path = self._format_json_path(list(error.absolute_path))
        return f"{path}: {error.message}"

    def validate(self, response: dict[str, Any], schema_ref: str) -> ValidationResult:
        """Validate a JSON response against a specific schema definition.

        Args:
            response: The JSON response to validate.
            schema_ref: The schema reference to validate against. Can be:
                       - A definition name (e.g., "Task")
                       - A full reference (e.g., "#/definitions/Task")

        Returns:
            A ValidationResult with validation status and any errors.
        """
        definition = self._get_definition(schema_ref)
        if definition is None:
            return ValidationResult(
                valid=False,
                errors=[f"Unknown schema reference: {schema_ref}"],
                schema_ref=schema_ref,
            )

        # Resolve all $refs in the definition
        resolved_definition = self._resolve_all_refs(definition)

        # Create a validator
        validator_cls = validator_for(resolved_definition)
        validator = validator_cls(resolved_definition)

        # Collect all errors
        errors = list(validator.iter_errors(response))

        if not errors:
            return ValidationResult(valid=True, errors=[], schema_ref=schema_ref)

        # Format all errors with JSON paths
        error_messages = [self._format_error(error) for error in errors]

        return ValidationResult(valid=False, errors=error_messages, schema_ref=schema_ref)

    def get_definition_names(self) -> list[str]:
        """Get all available definition names in the schema.

        Returns:
            A list of definition names.
        """
        return list(self._schema.get("definitions", {}).keys())
