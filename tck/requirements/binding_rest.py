"""HTTP+JSON/REST protocol binding requirements from A2A specification Section 11.

Covers: URL patterns, Content-Type, camelCase query params,
RFC 9457 Problem Details, SSE streaming.
"""

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    CONTENT_TYPE,
    ERROR,
    MAPPING,
    METHOD,
    PROBLEM_DETAILS,
    QUERY_PARAMS,
    REST,
    SERVICE_PARAMS,
    SSE,
    STREAMING,
    URL,
)


BINDING_REST_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="REST-URL-001",
        section="11.3",
        title="RESTful resource-based URL patterns",
        level=RequirementLevel.MUST,
        description=(
            "HTTP+JSON/REST binding MUST use the specified RESTful "
            "resource-based URL patterns for all operations."
        ),
        expected_behavior="Correct URL patterns used for each operation",
        spec_url=f"{SPEC_BASE}113-url-patterns-and-http-methods",
        tags=[REST, URL],
    ),
    RequirementSpec(
        id="REST-URL-002",
        section="11.3",
        title="Standard HTTP methods for each operation",
        level=RequirementLevel.MUST,
        description=(
            "HTTP+JSON/REST binding MUST use standard HTTP verbs: "
            "GET for retrieval, POST for creation/actions, DELETE for removal."
        ),
        expected_behavior="Correct HTTP methods used per operation",
        spec_url=f"{SPEC_BASE}113-url-patterns-and-http-methods",
        tags=[REST, METHOD],
    ),
    RequirementSpec(
        id="REST-SVC-001",
        section="11.1",
        title="Content-Type is application/json",
        level=RequirementLevel.MUST,
        description=(
            "HTTP+JSON/REST binding MUST use Content-Type application/json "
            "for requests and responses."
        ),
        expected_behavior="Content-Type header is application/json",
        spec_url=f"{SPEC_BASE}111-protocol-requirements",
        tags=[REST, CONTENT_TYPE],
    ),
    RequirementSpec(
        id="REST-SVC-002",
        section="11.2",
        title="Service parameters transmitted as HTTP headers",
        level=RequirementLevel.MUST,
        description=(
            "A2A service parameters MUST be transmitted using standard HTTP "
            "request headers for the REST binding."
        ),
        expected_behavior="A2A-Version and A2A-Extensions sent as HTTP headers",
        spec_url=f"{SPEC_BASE}112-service-parameter-transmission",
        tags=[REST, SERVICE_PARAMS],
    ),
    RequirementSpec(
        id="REST-QP-001",
        section="11.5",
        title="Query parameter names use camelCase",
        level=RequirementLevel.MUST,
        description=(
            "Query parameter names MUST use camelCase to match the JSON "
            "serialization of Protocol Buffer field names."
        ),
        expected_behavior="Query params like contextId, pageSize, pageToken",
        spec_url=f"{SPEC_BASE}115-query-parameter-naming-for-request-parameters",
        tags=[REST, QUERY_PARAMS],
    ),
    RequirementSpec(
        id="REST-ERR-001",
        section="11.6",
        title="Error responses use RFC 9457 Problem Details format",
        level=RequirementLevel.MUST,
        description=(
            "HTTP error responses MUST use RFC 9457 Problem Details format "
            "with Content-Type application/problem+json."
        ),
        expected_behavior="Error responses conform to Problem Details structure",
        spec_url=f"{SPEC_BASE}116-error-handling",
        tags=[REST, ERROR, PROBLEM_DETAILS],
    ),
    RequirementSpec(
        id="REST-ERR-002",
        section="11.6",
        title="A2A errors use specified type URIs",
        level=RequirementLevel.MUST,
        description=(
            "For A2A-specific errors, the type field MUST use the URI from "
            "the error code mappings table (e.g., "
            "https://a2a-protocol.org/errors/task-not-found)."
        ),
        expected_behavior="Error type field contains correct A2A URI",
        spec_url=f"{SPEC_BASE}116-error-handling",
        tags=[REST, ERROR, MAPPING],
    ),
    RequirementSpec(
        id="REST-SSE-001",
        section="11.7",
        title="REST streaming uses Server-Sent Events",
        level=RequirementLevel.MUST,
        description=(
            "REST streaming MUST use Server-Sent Events with the data field "
            "containing JSON serializations of StreamResponse objects."
        ),
        expected_behavior="SSE stream with StreamResponse JSON in data field",
        spec_url=f"{SPEC_BASE}117-streaming",
        tags=[REST, STREAMING, SSE],
    ),
]
