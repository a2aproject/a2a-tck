"""Proto Schema validator for A2A protocol gRPC responses.

This module provides validation of protobuf messages against proto descriptors,
including type checking, required field validation, and nested message validation.
"""

from __future__ import annotations

import warnings

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from google.protobuf.descriptor import FieldDescriptor


if TYPE_CHECKING:
    from google.protobuf.message import Message as ProtoMessage


# Field behavior values from google/api/field_behavior.proto
# FIELD_BEHAVIOR_REQUIRED = 2
FIELD_BEHAVIOR_REQUIRED = 2


def _is_repeated_field(field_desc: FieldDescriptor) -> bool:
    """Check if a field is repeated, handling API deprecations.

    Args:
        field_desc: The field descriptor.

    Returns:
        True if the field is repeated.
    """
    # Try the new API first — is_repeated is a property (not callable) on
    # newer UPB-based descriptors, or a method on older descriptors.
    if hasattr(field_desc, "is_repeated"):
        attr = field_desc.is_repeated
        return attr() if callable(attr) else attr

    # Fall back to the deprecated label property, suppressing the warning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return field_desc.label == FieldDescriptor.LABEL_REPEATED


@dataclass
class ValidationResult:
    """Result of a Proto Schema validation.

    Attributes:
        valid: True if the response passed validation.
        errors: List of error messages identifying field and reason.
        proto_type: The full name of the proto message type validated.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    proto_type: str = ""


class ProtoSchemaValidator:
    """Validates protobuf messages against proto message descriptors.

    This validator checks:
    - Type correctness (isinstance check)
    - Required field presence (based on field_behavior annotation)
    - Nested message validation (recursive)
    - Field constraints from proto definition

    Example:
        >>> from specification.generated import a2a_pb2
        >>> validator = ProtoSchemaValidator()
        >>> task = a2a_pb2.Task(id="123", context_id="ctx-1")
        >>> result = validator.validate(task, a2a_pb2.Task)
        >>> print(result.valid)
        True
    """

    def __init__(self) -> None:
        """Initialize the validator."""

    def validate(
        self, response: ProtoMessage, expected_type: type[ProtoMessage]
    ) -> ValidationResult:
        """Validate a proto message against an expected type.

        Args:
            response: The protobuf message to validate.
            expected_type: The expected protobuf message class.

        Returns:
            A ValidationResult with validation status and any errors.
        """
        errors: list[str] = []
        proto_type = expected_type.DESCRIPTOR.full_name

        # Type check
        if not isinstance(response, expected_type):
            actual_type = type(response).__name__
            if hasattr(response, "DESCRIPTOR"):
                actual_type = response.DESCRIPTOR.full_name
            errors.append(
                f"Type mismatch: expected {proto_type}, got {actual_type}"
            )
            return ValidationResult(valid=False, errors=errors, proto_type=proto_type)

        # Validate the message
        nested_errors = self._validate_message(response, "")
        errors.extend(nested_errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            proto_type=proto_type,
        )

    def _validate_message(self, message: ProtoMessage, path: str) -> list[str]:
        """Validate a proto message recursively.

        Args:
            message: The protobuf message to validate.
            path: The current field path for error messages.

        Returns:
            A list of error messages.
        """
        errors: list[str] = []
        descriptor = message.DESCRIPTOR

        for field_desc in descriptor.fields:
            field_path = f"{path}.{field_desc.name}" if path else field_desc.name
            field_errors = self._validate_field(message, field_desc, field_path)
            errors.extend(field_errors)

        return errors

    def _validate_field(
        self, message: ProtoMessage, field_desc: FieldDescriptor, path: str
    ) -> list[str]:
        """Validate a single field in a proto message.

        Args:
            message: The parent protobuf message.
            field_desc: The field descriptor.
            path: The current field path for error messages.

        Returns:
            A list of error messages.
        """
        errors: list[str] = []

        # Check if field is required
        is_required = self._is_field_required(field_desc)

        # Get the field value
        value = getattr(message, field_desc.name)

        # Check field presence for required fields
        if is_required and not self._is_field_set(message, field_desc, value):
            errors.append(f"{path}: required field is not set")
            return errors  # Don't validate further if required field is missing

        # For repeated fields, validate each item
        if _is_repeated_field(field_desc):
            if field_desc.message_type is not None:
                # Map fields are special
                if field_desc.message_type.GetOptions().map_entry:
                    # For map fields, validate values if they are messages
                    value_field = field_desc.message_type.fields_by_name.get("value")
                    if value_field and value_field.message_type is not None:
                        for key, map_value in value.items():
                            item_path = f"{path}[{key!r}]"
                            item_errors = self._validate_message(map_value, item_path)
                            errors.extend(item_errors)
                else:
                    # Regular repeated message field
                    for i, item in enumerate(value):
                        item_path = f"{path}[{i}]"
                        item_errors = self._validate_message(item, item_path)
                        errors.extend(item_errors)
        # Singular message field - validate if set
        elif field_desc.message_type is not None and message.HasField(field_desc.name):
            nested_errors = self._validate_message(value, path)
            errors.extend(nested_errors)

        return errors

    def _is_field_required(self, field_desc: FieldDescriptor) -> bool:
        """Check if a field is marked as required.

        In proto3, required fields are indicated by the field_behavior
        annotation from google/api/field_behavior.proto.

        Args:
            field_desc: The field descriptor.

        Returns:
            True if the field is required.
        """
        # Check for google.api.field_behavior annotation
        options = field_desc.GetOptions()

        # The field_behavior extension contains a list of behaviors
        # We need to check if FIELD_BEHAVIOR_REQUIRED (2) is in the list
        try:
            from google.api import field_behavior_pb2

            field_behaviors = options.Extensions[field_behavior_pb2.field_behavior]
            return FIELD_BEHAVIOR_REQUIRED in field_behaviors
        except (ImportError, KeyError):
            # If the extension is not available, fall back to checking serialized options
            # The serialized form of REQUIRED is '\xe0\x41\x02'
            serialized = field_desc.GetOptions().SerializeToString()
            # Look for the field_behavior extension marker followed by REQUIRED value
            # Field behavior extension number is 1052 (0x041C), value 2 means REQUIRED
            return b"\xe0\x41\x02" in serialized

    def _is_field_set(
        self, message: ProtoMessage, field_desc: FieldDescriptor, value: Any
    ) -> bool:
        """Check if a field is set (has a non-default value).

        Args:
            message: The parent message.
            field_desc: The field descriptor.
            value: The current field value.

        Returns:
            True if the field is set to a non-default value.
        """
        # For message fields, use HasField
        if field_desc.message_type is not None:
            if _is_repeated_field(field_desc):
                return len(value) > 0
            try:
                return message.HasField(field_desc.name)
            except ValueError:
                # HasField not supported for this field type
                return value is not None

        # For repeated fields, check if non-empty
        if _is_repeated_field(field_desc):
            return len(value) > 0

        # For scalar fields, check against default value
        default_value = field_desc.default_value

        # String fields
        if field_desc.type == FieldDescriptor.TYPE_STRING:
            return value != ""

        # Bytes fields
        if field_desc.type == FieldDescriptor.TYPE_BYTES:
            return value != b""

        # Numeric fields
        if field_desc.type in (
            FieldDescriptor.TYPE_INT32,
            FieldDescriptor.TYPE_INT64,
            FieldDescriptor.TYPE_UINT32,
            FieldDescriptor.TYPE_UINT64,
            FieldDescriptor.TYPE_SINT32,
            FieldDescriptor.TYPE_SINT64,
            FieldDescriptor.TYPE_FIXED32,
            FieldDescriptor.TYPE_FIXED64,
            FieldDescriptor.TYPE_SFIXED32,
            FieldDescriptor.TYPE_SFIXED64,
            FieldDescriptor.TYPE_FLOAT,
            FieldDescriptor.TYPE_DOUBLE,
        ):
            return value != 0

        # Boolean fields
        if field_desc.type == FieldDescriptor.TYPE_BOOL:
            return value is True

        # Enum fields
        if field_desc.type == FieldDescriptor.TYPE_ENUM:
            return value != 0

        return value != default_value
