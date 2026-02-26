"""Agent Card requirements from A2A specification Sections 5, 8.

Covers: Discovery, protocol declarations, required AgentCard fields,
extended card auth, JCS signing.
"""

from tck.requirements.base import (
    GET_EXTENDED_AGENT_CARD_BINDING,
    SPEC_BASE,
    OperationType,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    AGENT_CARD,
    AUTH,
    DISCOVERY,
    ERROR,
    EXTENDED,
    INTERFACE,
    JCS,
    JWS,
    PROTOCOL,
    SECURITY,
    SIGNING,
    STRUCTURE,
)


AGENT_CARD_REQUIREMENTS: list[RequirementSpec] = [
    # --- Discovery (Section 8.1) ---
    RequirementSpec(
        id="CARD-DISC-001",
        section="8.1",
        title="Agent Card must be available",
        level=RequirementLevel.MUST,
        description=(
            "A2A Servers MUST make an Agent Card available describing the "
            "server's identity, capabilities, skills, and interaction "
            "requirements."
        ),
        expected_behavior="Agent Card retrievable by clients",
        spec_url=f"{SPEC_BASE}81-purpose",
        tags=[AGENT_CARD, DISCOVERY],
    ),
    # --- Protocol Declaration (Section 8.3) ---
    RequirementSpec(
        id="CARD-PROTO-001",
        section="8.3",
        title="AgentCard must properly declare supported protocols",
        level=RequirementLevel.MUST,
        description=(
            "The AgentCard MUST properly declare supported protocols."
        ),
        expected_behavior="Supported protocols declared in AgentCard",
        spec_url=f"{SPEC_BASE}83-protocol-declaration-requirements",
        tags=[AGENT_CARD, PROTOCOL],
    ),
    RequirementSpec(
        id="CARD-PROTO-002",
        section="8.3.1",
        title="Each interface must declare transport and URL",
        level=RequirementLevel.MUST,
        description=(
            "Each interface in supportedInterfaces MUST accurately declare "
            "its transport protocol and URL."
        ),
        expected_behavior="Each interface has accurate transport and URL",
        spec_url=f"{SPEC_BASE}831-supported-interfaces-declaration",
        tags=[AGENT_CARD, PROTOCOL, INTERFACE],
    ),
    # --- AgentCard Required Fields (Section 4.4.1) ---
    RequirementSpec(
        id="CARD-STRUCT-001",
        section="4.4.1",
        title="AgentCard contains required fields",
        level=RequirementLevel.MUST,
        description=(
            "An AgentCard MUST contain all required fields as defined in "
            "the Protocol Buffer definition including name, description, "
            "supportedInterfaces, capabilities, and skills."
        ),
        expected_behavior="All required AgentCard fields present",
        spec_url=f"{SPEC_BASE}441-agentcard",
        tags=[AGENT_CARD, STRUCTURE],
    ),
    # --- Extended Agent Card (Section 3.1.11) ---
    RequirementSpec(
        id="CARD-EXT-001",
        section="3.1.11",
        title="Extended Agent Card requires authentication",
        level=RequirementLevel.MUST,
        description=(
            "The client MUST authenticate the GetExtendedAgentCard request "
            "using one of the schemes declared in the public AgentCard."
        ),
        operation=OperationType.GET_EXTENDED_AGENT_CARD,
        binding=GET_EXTENDED_AGENT_CARD_BINDING,
        proto_request_type="GetExtendedAgentCardRequest",
        proto_response_type="AgentCard",
        expected_behavior="Authenticated request returns extended card",
        spec_url=f"{SPEC_BASE}3111-get-extended-agent-card",
        tags=[AGENT_CARD, EXTENDED, AUTH],
    ),
    RequirementSpec(
        id="CARD-EXT-002",
        section="3.1.11",
        title="Extended card not configured returns specific error",
        level=RequirementLevel.MUST,
        description=(
            "If the agent declares support but has not configured an extended "
            "card, it MUST return ExtendedAgentCardNotConfiguredError."
        ),
        operation=OperationType.GET_EXTENDED_AGENT_CARD,
        binding=GET_EXTENDED_AGENT_CARD_BINDING,
        proto_request_type="GetExtendedAgentCardRequest",
        expected_behavior="ExtendedAgentCardNotConfiguredError returned",
        spec_url=f"{SPEC_BASE}3111-get-extended-agent-card",
        tags=[AGENT_CARD, EXTENDED, ERROR],
    ),
    # --- Agent Card Signing (Section 8.4) ---
    RequirementSpec(
        id="CARD-SIGN-001",
        section="8.4.1",
        title="Agent Card canonicalized with JCS before signing",
        level=RequirementLevel.MUST,
        description=(
            "Before signing, the Agent Card content MUST be canonicalized "
            "using the JSON Canonicalization Scheme (JCS) as defined in "
            "RFC 8785."
        ),
        expected_behavior="Agent Card canonicalized per RFC 8785 before signing",
        spec_url=f"{SPEC_BASE}841-canonicalization-requirements",
        tags=[AGENT_CARD, SIGNING, JCS],
    ),
    RequirementSpec(
        id="CARD-SIGN-002",
        section="8.4.1",
        title="Signatures field excluded from signed content",
        level=RequirementLevel.MUST,
        description=(
            "The signatures field itself MUST be excluded from the content "
            "being signed to avoid circular dependencies."
        ),
        expected_behavior="Signatures field excluded from signing payload",
        spec_url=f"{SPEC_BASE}841-canonicalization-requirements",
        tags=[AGENT_CARD, SIGNING],
    ),
    RequirementSpec(
        id="CARD-SIGN-003",
        section="8.4.2",
        title="Signature protected header includes required parameters",
        level=RequirementLevel.MUST,
        description=(
            "The JWS protected header MUST include alg (algorithm) and "
            "kid (key ID) parameters."
        ),
        expected_behavior="Protected header contains alg and kid",
        spec_url=f"{SPEC_BASE}842-signature-format",
        tags=[AGENT_CARD, SIGNING, JWS],
    ),
    RequirementSpec(
        id="CARD-SIGN-004",
        section="8.4.3",
        title="Expired or revoked keys must not be used for verification",
        level=RequirementLevel.MUST,
        description=(
            "Expired or revoked keys MUST NOT be used for signature "
            "verification."
        ),
        expected_behavior="Expired/revoked keys rejected during verification",
        spec_url=f"{SPEC_BASE}843-signature-verification",
        tags=[AGENT_CARD, SIGNING, SECURITY],
    ),
]
