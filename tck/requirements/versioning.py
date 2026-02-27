"""Versioning requirements from A2A specification Section 3.6.

Covers: A2A-Version header, version negotiation, default version.
"""

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    CLIENT,
    DEFAULT,
    ERROR,
    MULTI_OPERATION,
    SERVER,
    VERSIONING,
)


VERSIONING_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="VER-CLIENT-001",
        section="3.6.1",
        title="Clients must send A2A-Version header with each request",
        level=RequirementLevel.MUST,
        description=(
            "Clients MUST send the A2A-Version header with each request to "
            "maintain compatibility after an agent upgrades."
        ),
        expected_behavior="A2A-Version header present in every request",
        spec_url=f"{SPEC_BASE}361-client-responsibilities",
        tags=[VERSIONING, CLIENT],
    ),
    RequirementSpec(
        id="VER-SERVER-001",
        section="3.6.2",
        title="Agent processes requests using requested version semantics",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST process requests using the semantics of the "
            "requested A2A-Version (matching Major.Minor)."
        ),
        expected_behavior="Request processed per requested version",
        spec_url=f"{SPEC_BASE}362-server-responsibilities",
        tags=[VERSIONING, SERVER, MULTI_OPERATION],
    ),
    RequirementSpec(
        id="VER-SERVER-002",
        section="3.6.2",
        title="Agent returns VersionNotSupportedError for unsupported version",
        level=RequirementLevel.MUST,
        description=(
            "If the version is not supported by the interface, agents MUST "
            "return a VersionNotSupportedError."
        ),
        expected_behavior="VersionNotSupportedError returned",
        spec_url=f"{SPEC_BASE}362-server-responsibilities",
        tags=[VERSIONING, SERVER, ERROR],
    ),
    RequirementSpec(
        id="VER-SERVER-003",
        section="3.6.2",
        title="Agent interprets empty version header as 0.3",
        level=RequirementLevel.MUST,
        description=(
            "Agents MUST interpret an empty A2A-Version value as version 0.3."
        ),
        expected_behavior="Empty version treated as 0.3",
        spec_url=f"{SPEC_BASE}362-server-responsibilities",
        tags=[VERSIONING, SERVER, DEFAULT],
    ),
    RequirementSpec(
        id="VER-CLIENT-002",
        section="3.6",
        title="Patch version numbers must not affect negotiation",
        level=RequirementLevel.MUST,
        description=(
            "Patch version numbers MUST NOT be considered when clients and "
            "servers negotiate protocol versions. Patch version numbers "
            "SHOULD NOT be used in requests, responses and Agent Cards."
        ),
        expected_behavior="Patch versions ignored in negotiation",
        spec_url=f"{SPEC_BASE}36-versioning",
        tags=[VERSIONING],
    ),
]
