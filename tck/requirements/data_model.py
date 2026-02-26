"""Data model requirements from A2A specification Section 4.

Covers: Task structure, Message structure, Part oneof semantics,
Artifact structure, valid TaskState values, camelCase naming, timestamps.
"""

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    ARTIFACT,
    COMPATIBILITY,
    DATA_MODEL,
    ENUM,
    MESSAGE,
    PART,
    SERIALIZATION,
    STATUS,
    TASK,
    TIMESTAMP,
    VALIDATION,
)


DATA_MODEL_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="DM-TASK-001",
        section="4.1.1",
        title="Task object contains required fields",
        level=RequirementLevel.MUST,
        description=(
            "A Task object MUST contain required fields: id, contextId, "
            "and status as defined in the Protocol Buffer definition."
        ),
        expected_behavior="Task objects include all required fields",
        spec_url=f"{SPEC_BASE}411-task",
        tags=[DATA_MODEL, TASK],
    ),
    RequirementSpec(
        id="DM-TASK-002",
        section="4.1.3",
        title="TaskState uses valid enumeration values",
        level=RequirementLevel.MUST,
        description=(
            "TaskState values MUST be one of the defined enumeration values: "
            "submitted, working, input_required, auth_required, completed, "
            "failed, canceled, rejected."
        ),
        expected_behavior="Only valid TaskState enum values used",
        spec_url=f"{SPEC_BASE}413-taskstate",
        tags=[DATA_MODEL, TASK, ENUM],
    ),
    RequirementSpec(
        id="DM-MSG-001",
        section="4.1.4",
        title="Message contains required fields",
        level=RequirementLevel.MUST,
        description=(
            "A Message object MUST contain required fields: role, parts, "
            "and messageId as defined in the Protocol Buffer definition."
        ),
        expected_behavior="Message objects include all required fields",
        spec_url=f"{SPEC_BASE}414-message",
        tags=[DATA_MODEL, MESSAGE],
    ),
    RequirementSpec(
        id="DM-MSG-002",
        section="4.1.5",
        title="Role uses valid enumeration values",
        level=RequirementLevel.MUST,
        description=(
            "Role values MUST be one of the defined values: user or agent."
        ),
        expected_behavior="Only valid Role enum values used",
        spec_url=f"{SPEC_BASE}415-role",
        tags=[DATA_MODEL, MESSAGE, ENUM],
    ),
    RequirementSpec(
        id="DM-PART-001",
        section="4.1.6",
        title="Part uses oneof semantics",
        level=RequirementLevel.MUST,
        description=(
            "A Part object MUST contain exactly one of: text, file "
            "(raw bytes or URL reference), or data (structured JSON)."
        ),
        expected_behavior="Part contains exactly one content type",
        spec_url=f"{SPEC_BASE}416-part",
        tags=[DATA_MODEL, PART],
    ),
    RequirementSpec(
        id="DM-ART-001",
        section="4.1.7",
        title="Artifact contains required fields",
        level=RequirementLevel.MUST,
        description=(
            "An Artifact object MUST contain required fields: artifactId "
            "and parts as defined in the Protocol Buffer definition."
        ),
        expected_behavior="Artifact objects include all required fields",
        spec_url=f"{SPEC_BASE}417-artifact",
        tags=[DATA_MODEL, ARTIFACT],
    ),
    RequirementSpec(
        id="DM-STATUS-001",
        section="4.1.2",
        title="TaskStatus contains required state field",
        level=RequirementLevel.MUST,
        description=(
            "A TaskStatus object MUST contain the state field with a valid "
            "TaskState value."
        ),
        expected_behavior="TaskStatus includes state field",
        spec_url=f"{SPEC_BASE}412-taskstatus",
        tags=[DATA_MODEL, TASK, STATUS],
    ),
    RequirementSpec(
        id="DM-SERIAL-001",
        section="5.5",
        title="JSON serialization uses camelCase field names",
        level=RequirementLevel.MUST,
        description=(
            "All JSON serializations of the A2A protocol data model MUST use "
            "camelCase naming for field names, not snake_case."
        ),
        expected_behavior="All JSON field names use camelCase",
        spec_url=f"{SPEC_BASE}55-json-field-naming-convention",
        tags=[DATA_MODEL, SERIALIZATION],
    ),
    RequirementSpec(
        id="DM-SERIAL-002",
        section="5.5",
        title="Enum values use ProtoJSON string representation",
        level=RequirementLevel.MUST,
        description=(
            "Enum values MUST be represented according to the ProtoJSON "
            "specification as their string names as defined in the Protocol "
            "Buffer definition (typically SCREAMING_SNAKE_CASE)."
        ),
        expected_behavior="Enum values serialized as proto string names",
        spec_url=f"{SPEC_BASE}55-json-field-naming-convention",
        tags=[DATA_MODEL, SERIALIZATION, ENUM],
    ),
    RequirementSpec(
        id="DM-SERIAL-003",
        section="5.6.1",
        title="Timestamps use ISO 8601 format in UTC",
        level=RequirementLevel.MUST,
        description=(
            "Timestamps MUST be represented as ISO 8601 formatted strings in "
            "UTC timezone. Timestamps MUST NOT include timezone offsets other "
            "than 'Z'."
        ),
        expected_behavior="Timestamps formatted as ISO 8601 with Z suffix",
        spec_url=f"{SPEC_BASE}561-timestamps",
        tags=[DATA_MODEL, SERIALIZATION, TIMESTAMP],
    ),
    RequirementSpec(
        id="DM-SERIAL-004",
        section="5.7",
        title="Required fields must be present in messages",
        level=RequirementLevel.MUST,
        description=(
            "Fields marked with REQUIRED field_behavior annotation MUST be "
            "present and set in valid messages. Arrays marked as required "
            "MUST contain at least one element."
        ),
        expected_behavior="Required fields present and set",
        spec_url=f"{SPEC_BASE}57-field-presence-and-optionality",
        tags=[DATA_MODEL, VALIDATION],
    ),
    RequirementSpec(
        id="DM-SERIAL-005",
        section="5.7",
        title="Implementations should ignore unrecognized fields",
        level=RequirementLevel.SHOULD,
        description=(
            "Implementations SHOULD ignore unrecognized fields in messages, "
            "allowing for forward compatibility as the protocol evolves."
        ),
        expected_behavior="Unrecognized fields ignored without error",
        spec_url=f"{SPEC_BASE}57-field-presence-and-optionality",
        tags=[DATA_MODEL, COMPATIBILITY],
    ),
]
