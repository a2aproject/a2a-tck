"""Tests for the JSON Schema validator."""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from tck.validators.json_schema import JSONSchemaValidator, ValidationResult


@pytest.fixture
def schema_path() -> Path:
    """Get the path to the a2a.json schema."""
    return Path(__file__).parent.parent.parent.parent / "specification" / "a2a.json"


@pytest.fixture
def validator(schema_path: Path) -> JSONSchemaValidator:
    """Create a JSONSchemaValidator instance."""
    return JSONSchemaValidator(schema_path)


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ValidationResult(valid=True, errors=[], schema_ref="Task")
        assert result.valid is True
        assert result.errors == []
        assert result.schema_ref == "Task"

    def test_invalid_result(self) -> None:
        """Test creating an invalid result with errors."""
        result = ValidationResult(
            valid=False,
            errors=["$.status: 'invalid' is not valid"],
            schema_ref="Task",
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.schema_ref == "Task"

    def test_default_values(self) -> None:
        """Test default values for errors and schema_ref."""
        result = ValidationResult(valid=True)
        assert result.errors == []
        assert result.schema_ref == ""


class TestJSONSchemaValidatorInit:
    """Tests for JSONSchemaValidator initialization."""

    def test_loads_schema(self, schema_path: Path) -> None:
        """Test that the schema is loaded without errors."""
        validator = JSONSchemaValidator(schema_path)
        # Verify the validator is functional by checking it can validate
        result = validator.validate({"id": "task-1", "context_id": "ctx-1", "status": {}}, "Task")
        assert result is not None

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing schema."""
        with pytest.raises(FileNotFoundError):
            JSONSchemaValidator(tmp_path / "nonexistent.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Test that JSONDecodeError is raised for invalid JSON."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json }")
        with pytest.raises(json.JSONDecodeError):
            JSONSchemaValidator(invalid_json)


class TestJSONSchemaValidatorValidate:
    """Tests for the validate method."""

    def test_valid_task(self, validator: JSONSchemaValidator) -> None:
        """Test validating a valid Task object."""
        task = {
            "id": "task-123",
            "contextId": "ctx-456",
            "status": {
                "state": "TASK_STATE_WORKING",
            },
        }
        result = validator.validate(task, "Task")
        assert result.valid is True
        assert result.errors == []
        assert result.schema_ref == "Task"

    def test_valid_agent_card(self, validator: JSONSchemaValidator) -> None:
        """Test validating a valid Agent Card object."""
        agent_card = {
            "name": "Test Agent",
            "description": "A test agent",
            "version": "1.0.0",
        }
        result = validator.validate(agent_card, "Agent Card")
        assert result.valid is True
        assert result.errors == []

    def test_invalid_task_extra_property(self, validator: JSONSchemaValidator) -> None:
        """Test that additional properties are rejected."""
        task = {
            "id": "task-123",
            "unknownField": "should fail",
        }
        result = validator.validate(task, "Task")
        assert result.valid is False
        assert len(result.errors) >= 1
        # Check that error mentions the unknown field
        assert any("unknownField" in error for error in result.errors)

    def test_invalid_type(self, validator: JSONSchemaValidator) -> None:
        """Test that wrong types are rejected."""
        task = {
            "id": 123,  # Should be string
        }
        result = validator.validate(task, "Task")
        assert result.valid is False
        assert any("id" in error for error in result.errors)

    def test_collects_multiple_errors(self, validator: JSONSchemaValidator) -> None:
        """Test that all errors are collected, not just the first."""
        task = {
            "id": 123,  # Wrong type
            "contextId": 456,  # Wrong type
            "unknownField": "extra",  # Additional property
        }
        result = validator.validate(task, "Task")
        assert result.valid is False
        # Should have multiple errors
        min_expected_errors = 2
        assert len(result.errors) >= min_expected_errors

    def test_error_includes_json_path(self, validator: JSONSchemaValidator) -> None:
        """Test that errors include JSON path."""
        task = {
            "id": 123,  # Wrong type
        }
        result = validator.validate(task, "Task")
        assert result.valid is False
        # Check that path notation is used
        assert any("$.id" in error or "$['id']" in error for error in result.errors)

    def test_nested_error_path(self, validator: JSONSchemaValidator) -> None:
        """Test that nested errors have correct JSON paths."""
        task = {
            "id": "task-123",
            "status": {
                "state": "invalid_state",  # Invalid state value
            },
        }
        result = validator.validate(task, "Task")
        assert result.valid is False
        # Should reference the nested path
        assert any("status" in error for error in result.errors)

    def test_array_error_path(self, validator: JSONSchemaValidator) -> None:
        """Test that array errors have correct JSON paths with indices."""
        task = {
            "id": "task-123",
            "artifacts": [
                {"name": "valid"},
                {"name": 123},  # Invalid type in array
            ],
        }
        result = validator.validate(task, "Task")
        assert result.valid is False
        # Should reference the array index
        error_text = " ".join(result.errors)
        assert "artifacts" in error_text

    def test_unknown_schema_ref(self, validator: JSONSchemaValidator) -> None:
        """Test that unknown schema references return error."""
        result = validator.validate({}, "NonExistentType")
        assert result.valid is False
        assert any("Unknown schema reference" in error for error in result.errors)


class TestSchemaRefFormats:
    """Tests for different schema reference formats."""

    def test_definition_name(self, validator: JSONSchemaValidator) -> None:
        """Test using direct definition name."""
        result = validator.validate({"id": "123"}, "Task")
        assert result.valid is True

    def test_full_ref_format(self, validator: JSONSchemaValidator) -> None:
        """Test using #/definitions/... format."""
        result = validator.validate({"id": "123"}, "#/definitions/Task")
        assert result.valid is True

    def test_defs_format(self, validator: JSONSchemaValidator) -> None:
        """Test using #/$defs/... format (alias)."""
        result = validator.validate({"id": "123"}, "#/$defs/Task")
        assert result.valid is True

    def test_space_in_name(self, validator: JSONSchemaValidator) -> None:
        """Test definition names with spaces."""
        result = validator.validate({"name": "Test"}, "Agent Card")
        assert result.valid is True

    def test_camelcase_to_spaces(self, validator: JSONSchemaValidator) -> None:
        """Test that CamelCase is converted to space-separated."""
        # "TaskStatus" should find "Task Status"
        result = validator.validate({"state": "TASK_STATE_COMPLETED"}, "TaskStatus")
        assert result.valid is True


class TestGetDefinitionNames:
    """Tests for get_definition_names method."""

    def test_returns_list(self, validator: JSONSchemaValidator) -> None:
        """Test that definition names are returned as a list."""
        names = validator.get_definition_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_contains_expected_definitions(self, validator: JSONSchemaValidator) -> None:
        """Test that expected definitions are present."""
        names = validator.get_definition_names()
        assert "Task" in names
        assert "Agent Card" in names
        assert "Message" in names


class TestRefResolution:
    """Tests for $ref resolution."""

    def test_resolves_nested_refs(self, validator: JSONSchemaValidator) -> None:
        """Test that nested $refs are resolved correctly."""
        # Task contains status which refs TaskStatus
        task = {
            "id": "task-123",
            "status": {
                "state": "TASK_STATE_COMPLETED",
            },
        }
        result = validator.validate(task, "Task")
        assert result.valid is True

    def test_resolves_array_item_refs(self, validator: JSONSchemaValidator) -> None:
        """Test that $refs in array items are resolved."""
        # Task.artifacts refs Artifact
        task = {
            "id": "task-123",
            "artifacts": [
                {
                    "artifactId": "artifact-1",
                    "name": "output",
                },
            ],
        }
        result = validator.validate(task, "Task")
        assert result.valid is True
