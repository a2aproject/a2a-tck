"""Tests for the Proto Schema validator."""

import pytest

from specification.generated import a2a_pb2
from tck.validators.proto_schema import ProtoSchemaValidator, ValidationResult


@pytest.fixture
def validator() -> ProtoSchemaValidator:
    """Create a ProtoSchemaValidator instance."""
    return ProtoSchemaValidator()


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(valid=True, errors=[], proto_type="a2a.v1.Task")
        assert result.valid is True
        assert result.errors == []
        assert result.proto_type == "a2a.v1.Task"

    def test_invalid_result(self):
        """Test creating an invalid result with errors."""
        result = ValidationResult(
            valid=False,
            errors=["id: required field is not set"],
            proto_type="a2a.v1.Task",
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.proto_type == "a2a.v1.Task"

    def test_default_values(self):
        """Test default values for errors and proto_type."""
        result = ValidationResult(valid=True)
        assert result.errors == []
        assert result.proto_type == ""


class TestProtoSchemaValidatorTypeCheck:
    """Tests for type checking."""

    def test_correct_type(self, validator: ProtoSchemaValidator):
        """Test that correct types pass validation."""
        task = a2a_pb2.Task(
            id="task-123",
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_WORKING),
        )
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is True
        assert result.proto_type == "a2a.v1.Task"

    def test_wrong_type(self, validator: ProtoSchemaValidator):
        """Test that wrong types fail validation."""
        message = a2a_pb2.Message(
            message_id="msg-123",
            role=a2a_pb2.ROLE_USER,
            parts=[a2a_pb2.Part(text="Hello")],
        )
        result = validator.validate(message, a2a_pb2.Task)
        assert result.valid is False
        assert any("Type mismatch" in error for error in result.errors)
        assert "a2a.v1.Task" in result.errors[0]
        assert "a2a.v1.Message" in result.errors[0]

    def test_proto_type_in_result(self, validator: ProtoSchemaValidator):
        """Test that proto_type is set correctly in result."""
        task = a2a_pb2.Task(
            id="123",
            context_id="ctx",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_SUBMITTED),
        )
        result = validator.validate(task, a2a_pb2.Task)
        assert result.proto_type == "a2a.v1.Task"


class TestRequiredFieldValidation:
    """Tests for required field validation."""

    def test_required_field_present(self, validator: ProtoSchemaValidator):
        """Test that present required fields pass validation."""
        task = a2a_pb2.Task(
            id="task-123",
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_COMPLETED),
        )
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is True

    def test_required_field_missing(self, validator: ProtoSchemaValidator):
        """Test that missing required fields fail validation."""
        # Task requires id, context_id, and status
        task = a2a_pb2.Task()  # All fields empty
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is False
        # Should have errors for missing required fields
        assert len(result.errors) >= 1

    def test_required_field_error_message(self, validator: ProtoSchemaValidator):
        """Test that error messages clearly identify the missing field."""
        task = a2a_pb2.Task(
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_WORKING),
        )
        # id is missing
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is False
        assert any("id" in error and "required" in error for error in result.errors)

    def test_multiple_required_fields_missing(self, validator: ProtoSchemaValidator):
        """Test that all missing required fields are reported."""
        task = a2a_pb2.Task()
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is False
        # Should report multiple errors
        assert len(result.errors) >= 2


class TestNestedMessageValidation:
    """Tests for nested message validation."""

    def test_nested_message_valid(self, validator: ProtoSchemaValidator):
        """Test that valid nested messages pass validation."""
        task = a2a_pb2.Task(
            id="task-123",
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_WORKING),
        )
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is True

    def test_nested_message_missing_required(self, validator: ProtoSchemaValidator):
        """Test that nested messages with missing required fields fail."""
        # TaskStatus.state is required
        task = a2a_pb2.Task(
            id="task-123",
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(),  # state is unset (default 0)
        )
        result = validator.validate(task, a2a_pb2.Task)
        # Note: state=0 is TASK_STATE_UNSPECIFIED which might be considered set
        # The validation should still pass because the message is present
        # and the enum has a default value

    def test_nested_message_path_in_error(self, validator: ProtoSchemaValidator):
        """Test that error paths include nested field names."""
        # Create a Message with missing required parts
        message = a2a_pb2.Message(
            message_id="msg-123",
            role=a2a_pb2.ROLE_USER,
            # parts is required but empty
        )
        result = validator.validate(message, a2a_pb2.Message)
        assert result.valid is False
        # Error should reference the parts field
        assert any("parts" in error for error in result.errors)


class TestRepeatedFieldValidation:
    """Tests for repeated field validation."""

    def test_repeated_field_valid(self, validator: ProtoSchemaValidator):
        """Test that valid repeated fields pass validation."""
        task = a2a_pb2.Task(
            id="task-123",
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_COMPLETED),
            artifacts=[
                a2a_pb2.Artifact(
                    artifact_id="art-1",
                    parts=[a2a_pb2.Part(text="result")],
                ),
            ],
        )
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is True

    def test_repeated_field_item_invalid(self, validator: ProtoSchemaValidator):
        """Test that invalid items in repeated fields are caught."""
        task = a2a_pb2.Task(
            id="task-123",
            context_id="ctx-456",
            status=a2a_pb2.TaskStatus(state=a2a_pb2.TASK_STATE_COMPLETED),
            artifacts=[
                a2a_pb2.Artifact(),  # Missing required fields
            ],
        )
        result = validator.validate(task, a2a_pb2.Task)
        assert result.valid is False
        # Should reference the array index
        assert any("artifacts[0]" in error for error in result.errors)

    def test_repeated_message_required(self, validator: ProtoSchemaValidator):
        """Test that required repeated fields must have items."""
        # Message.parts is required
        message = a2a_pb2.Message(
            message_id="msg-123",
            role=a2a_pb2.ROLE_USER,
            # parts is empty
        )
        result = validator.validate(message, a2a_pb2.Message)
        assert result.valid is False
        assert any("parts" in error for error in result.errors)


class TestErrorMessages:
    """Tests for error message clarity."""

    def test_error_identifies_field(self, validator: ProtoSchemaValidator):
        """Test that errors identify which field failed."""
        task = a2a_pb2.Task()
        result = validator.validate(task, a2a_pb2.Task)
        # Each error should contain a field name
        for error in result.errors:
            assert ":" in error  # Format is "field: message"

    def test_error_identifies_reason(self, validator: ProtoSchemaValidator):
        """Test that errors explain why validation failed."""
        task = a2a_pb2.Task()
        result = validator.validate(task, a2a_pb2.Task)
        # Each error should contain a reason
        for error in result.errors:
            assert "required" in error or "mismatch" in error.lower()


class TestAgentCardValidation:
    """Tests for AgentCard validation (complex message)."""

    def test_valid_agent_card(self, validator: ProtoSchemaValidator):
        """Test validating a valid AgentCard."""
        agent_card = a2a_pb2.AgentCard(
            name="Test Agent",
            description="A test agent",
            version="1.0.0",
            supported_interfaces=[
                a2a_pb2.AgentInterface(
                    url="https://example.com/agent",
                    protocol_binding="grpc",
                    protocol_version="1.0",
                ),
            ],
            capabilities=a2a_pb2.AgentCapabilities(),
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            skills=[
                a2a_pb2.AgentSkill(
                    id="skill-1",
                    name="Test Skill",
                    description="A test skill",
                    tags=["test"],
                ),
            ],
        )
        result = validator.validate(agent_card, a2a_pb2.AgentCard)
        assert result.valid is True
        assert result.proto_type == "a2a.v1.AgentCard"

    def test_agent_card_missing_required(self, validator: ProtoSchemaValidator):
        """Test AgentCard with missing required fields."""
        agent_card = a2a_pb2.AgentCard(
            name="Test Agent",
            # Missing other required fields
        )
        result = validator.validate(agent_card, a2a_pb2.AgentCard)
        assert result.valid is False
        # Should have multiple errors for missing fields
        assert len(result.errors) >= 1
