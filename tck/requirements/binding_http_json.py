"""HTTP+JSON/REST protocol binding requirements from A2A specification Section 11.

Covers: URL patterns, Content-Type, camelCase query params,
AIP-193 error format, SSE streaming.
"""

from __future__ import annotations

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    AIP193,
    CONTENT_TYPE,
    ERROR,
    ERRORINFO,
    MAPPING,
    METHOD,
    QUERY_PARAMS,
    REST,
    SERVICE_PARAMS,
    SSE,
    STATUS,
    STREAMING,
    URL,
)


BINDING_HTTP_JSON_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="HTTP_JSON-URL-001",
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
        id="HTTP_JSON-URL-002",
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
        id="HTTP_JSON-SVC-001",
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
        id="HTTP_JSON-SVC-002",
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
        id="HTTP_JSON-QP-001",
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
        id="HTTP_JSON-ERR-001",
        section="11.6",
        title="Error responses use AIP-193 format",
        level=RequirementLevel.MUST,
        description=(
            "HTTP error responses MUST use the AIP-193 representation with "
            "Content-Type application/json containing an error object with "
            "code, status, message, and details fields."
        ),
        expected_behavior="Error responses conform to AIP-193 structure",
        spec_url=f"{SPEC_BASE}116-error-handling",
        tags=[REST, ERROR, AIP193],
    ),
    RequirementSpec(
        id="HTTP_JSON-ERR-002",
        section="11.6",
        title="A2A errors include ErrorInfo in details array",
        level=RequirementLevel.MUST,
        description=(
            "For A2A-specific errors, implementations MUST include a "
            "google.rpc.ErrorInfo message in the details array with reason "
            "(UPPER_SNAKE_CASE), domain (a2a-protocol.org), and optional metadata."
        ),
        expected_behavior="Error details array contains ErrorInfo with correct reason and domain",
        spec_url=f"{SPEC_BASE}116-error-handling",
        tags=[REST, ERROR, ERRORINFO, MAPPING],
    ),
    RequirementSpec(
        id="HTTP_JSON-STATUS-001",
        section="5.4",
        title="A2A errors map to correct HTTP status codes",
        level=RequirementLevel.MUST,
        description=(
            "Each A2A error type MUST map to the HTTP status code specified "
            "in the error code mappings table (e.g., TaskNotFoundError to "
            "404, ContentTypeNotSupportedError to 415)."
        ),
        expected_behavior="HTTP status code matches the spec-defined mapping for each error",
        spec_url=f"{SPEC_BASE}54-error-code-mappings",
        tags=[REST, ERROR, STATUS, MAPPING],
    ),
    RequirementSpec(
        id="HTTP_JSON-SSE-001",
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
