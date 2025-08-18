from agent_executor import (
    TckCoreAgentExecutor,  # type: ignore[import-untyped]
)

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    HTTPAuthSecurityScheme,
    OAuth2SecurityScheme,
    SecurityScheme,
    OAuthFlows,
    AuthorizationCodeOAuthFlow,
)


def main() -> None:
    """Main entry point for the TCK Core Agent."""

    # Define security schemes using A2A SDK types
    http_bearer_scheme = SecurityScheme(
        root=HTTPAuthSecurityScheme(type="http", scheme="bearer", description="HTTP Bearer token authentication")
    )

    oauth2_scheme = SecurityScheme(
        root=OAuth2SecurityScheme(
            type="oauth2",
            description="OAuth 2.0 authentication",
            flows=OAuthFlows(
                authorizationCode=AuthorizationCodeOAuthFlow(
                    authorizationUrl="https://auth.example.com/oauth/authorize",
                    tokenUrl="https://auth.example.com/oauth/token",
                    scopes={"read": "Read access", "write": "Write access"},
                )
            ),
        )
    )

    security_schemes = {"bearerAuth": http_bearer_scheme, "oauth2": oauth2_scheme}

    # Create agent card with enhanced capabilities and security
    agent_card = AgentCard(
        name="TCK Core Agent",
        description="A complete A2A agent implementation designed specifically for testing with the A2A Technology Compatibility Kit (TCK)",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[
            AgentSkill(
                id="tck_core_agent",
                name="TCK Core Agent",
                description="A complete A2A agent implementation designed for TCK testing",
                examples=["hi", "hello world", "how are you", "goodbye"],
                tags=["tck", "testing", "core", "complete"],
            )
        ],
        capabilities=AgentCapabilities(streaming=True),
        url="http://localhost:9999/",
        securitySchemes=security_schemes,
        security=[{"bearerAuth": []}, {"oauth2": ["read", "write"]}],
    )

    # Create task store and agent executor
    task_store = InMemoryTaskStore()
    agent_executor = TckCoreAgentExecutor()

    # Create the application using standard SDK class (no authentication enforcement)
    # Note: SDK doesn't provide built-in authentication middleware
    # Using SDK DefaultRequestHandler - historyLength parameter not implemented (SDK limitation)
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(agent_executor=agent_executor, task_store=task_store),
    )

    # Build the Starlette app without authentication middleware
    # Authentication will be tested but expected to fail due to SDK limitations
    starlette_app = app.build()

    # Start the server using uvicorn
    import uvicorn

    print("Starting TCK Core Agent on http://localhost:9999")
    print("Note: Authentication schemes declared in Agent Card but not enforced (SDK limitation)")
    print("Authentication tests will document SDK gaps with pytest.xfail")
    uvicorn.run(starlette_app, host="0.0.0.0", port=9999)


if __name__ == "__main__":
    main()
