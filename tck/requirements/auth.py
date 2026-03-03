"""Authentication and authorization requirements from A2A specification Sections 7, 13.

Covers: TLS requirements, server authentication, client authentication,
in-task auth, authorization scoping.
"""

from __future__ import annotations

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    AUTH,
    AUTHORIZATION,
    IN_TASK,
    NOT_AUTOMATABLE,
    SCOPE,
    SECURITY,
    SERVER,
    TLS,
)


AUTH_REQUIREMENTS: list[RequirementSpec] = [
    # --- Protocol Security (Section 7.1) ---
    RequirementSpec(
        id="AUTH-TLS-001",
        section="7.1",
        title="Production deployments must use encrypted communication",
        level=RequirementLevel.MUST,
        description=(
            "Production deployments MUST use encrypted communication "
            "(HTTPS for HTTP-based bindings, TLS for gRPC)."
        ),
        expected_behavior="All production traffic encrypted via TLS",
        spec_url=f"{SPEC_BASE}71-protocol-security",
        tags=[AUTH, TLS, SECURITY, NOT_AUTOMATABLE],
    ),
    RequirementSpec(
        id="AUTH-TLS-002",
        section="7.1",
        title="Modern TLS configurations recommended",
        level=RequirementLevel.SHOULD,
        description=(
            "Implementations SHOULD use modern TLS configurations "
            "(TLS 1.3+ recommended) with strong cipher suites."
        ),
        expected_behavior="TLS 1.3+ with strong ciphers used",
        spec_url=f"{SPEC_BASE}71-protocol-security",
        tags=[AUTH, TLS, SECURITY, NOT_AUTOMATABLE],
    ),
    # --- Server Identity (Section 7.2) ---
    RequirementSpec(
        id="AUTH-SERVER-001",
        section="7.2",
        title="Clients should verify server TLS certificates",
        level=RequirementLevel.SHOULD,
        description=(
            "A2A Clients SHOULD verify the A2A Server's identity by "
            "validating its TLS certificate against trusted CAs."
        ),
        expected_behavior="Server TLS certificate validated against trusted CAs",
        spec_url=f"{SPEC_BASE}72-server-identity-verification",
        tags=[AUTH, SERVER, TLS, NOT_AUTOMATABLE],
    ),
    # --- Server Authentication (Section 7.4) ---
    RequirementSpec(
        id="AUTH-SERVER-002",
        section="7.4",
        title="Server must authenticate every incoming request",
        level=RequirementLevel.MUST,
        description=(
            "The A2A Server MUST authenticate every incoming request based "
            "on the provided credentials and its declared authentication "
            "requirements."
        ),
        expected_behavior="Every request authenticated",
        spec_url=f"{SPEC_BASE}74-server-authentication-responsibilities",
        tags=[AUTH, SERVER],
    ),
    # --- In-Task Authentication (Section 7.5) ---
    RequirementSpec(
        id="AUTH-INTASK-001",
        section="7.5",
        title="Agent transitions to auth_required state for secondary credentials",
        level=RequirementLevel.SHOULD,
        description=(
            "If an agent requires additional credentials during task execution, "
            "it SHOULD transition the task to the TASK_STATE_AUTH_REQUIRED state."
        ),
        expected_behavior="Task transitions to auth_required when more creds needed",
        spec_url=f"{SPEC_BASE}75-in-task-authentication-secondary-credentials",
        tags=[AUTH, IN_TASK],
    ),
    # --- Authorization Scoping (Section 13.1) ---
    RequirementSpec(
        id="AUTH-SCOPE-001",
        section="13.1",
        title="Authorization checks on every operation request",
        level=RequirementLevel.MUST,
        description=(
            "Servers MUST implement authorization checks on every A2A "
            "Protocol Operations request."
        ),
        expected_behavior="Authorization verified for every request",
        spec_url=f"{SPEC_BASE}131-data-access-and-authorization-scoping",
        tags=[AUTH, AUTHORIZATION, SCOPE],
    ),
    RequirementSpec(
        id="AUTH-SCOPE-002",
        section="13.1",
        title="Results scoped to caller's authorization boundaries",
        level=RequirementLevel.MUST,
        description=(
            "Implementations MUST scope results to the caller's authorized "
            "access boundaries as defined by the agent's authorization model."
        ),
        expected_behavior="Results limited to authorized scope",
        spec_url=f"{SPEC_BASE}131-data-access-and-authorization-scoping",
        tags=[AUTH, AUTHORIZATION, SCOPE],
    ),
    RequirementSpec(
        id="AUTH-SCOPE-003",
        section="3.3.2",
        title="Server must not reveal existence of unauthorized resources",
        level=RequirementLevel.MUST,
        description=(
            "Servers MUST NOT reveal the existence of resources the client "
            "is not authorized to access."
        ),
        expected_behavior="Unauthorized resources invisible to client",
        spec_url=f"{SPEC_BASE}332-error-handling",
        tags=[AUTH, AUTHORIZATION, SECURITY],
    ),
]
