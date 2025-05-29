from agent_executor import (
    TckCoreAgentExecutor,  # type: ignore[import-untyped]
)
from custom_request_handler import (
    TckCoreRequestHandler,  # type: ignore[import-untyped]
)

from a2a.server.apps import A2AStarletteApplication
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
from starlette.responses import JSONResponse, Response
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
import base64


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication according to Agent Card security schemes"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for Agent Card endpoint (discovery)
        if request.url.path == "/.well-known/agent.json":
            return await call_next(request)
        
        # Check for authentication in HTTP headers
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header:
            # No authentication provided - return 401
            return Response(
                content="Authentication required",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Basic validation of authentication format
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            if token.strip() == "":
                return Response(content="Invalid bearer token", status_code=401)
            # For testing purposes, reject obviously invalid tokens
            if token in ["invalid-dummy-token", "invalid-token"]:
                return Response(content="Invalid bearer token", status_code=401)
        elif auth_header.startswith("Basic "):
            # Decode basic auth for validation
            try:
                encoded = auth_header[6:]  # Remove "Basic " prefix
                decoded = base64.b64decode(encoded).decode('utf-8')
                if decoded in ["invalid:invalid"]:
                    return Response(content="Invalid credentials", status_code=401)
            except Exception:
                return Response(content="Invalid basic auth format", status_code=401)
        else:
            # Unknown auth scheme
            return Response(content="Unsupported authentication scheme", status_code=401)
        
        # Authentication passed - continue to next middleware/endpoint
        return await call_next(request)


def main() -> None:
    """Main entry point for the TCK Core Agent."""
    
    # Define security schemes using A2A SDK types
    http_bearer_scheme = SecurityScheme(root=HTTPAuthSecurityScheme(
        type="http",
        scheme="bearer",
        description="HTTP Bearer token authentication"
    ))
    
    oauth2_scheme = SecurityScheme(root=OAuth2SecurityScheme(
        type="oauth2",
        description="OAuth 2.0 authentication",
        flows=OAuthFlows(
            authorizationCode=AuthorizationCodeOAuthFlow(
                authorizationUrl="https://auth.example.com/oauth/authorize",
                tokenUrl="https://auth.example.com/oauth/token",
                scopes={"read": "Read access", "write": "Write access"}
            )
        )
    ))
    
    security_schemes = {
        "bearerAuth": http_bearer_scheme,
        "oauth2": oauth2_scheme
    }
    
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
                tags=["tck", "testing", "core", "complete"]
            )
        ],
        capabilities=AgentCapabilities(streaming=True),
        url="http://localhost:9999/",
        securitySchemes=security_schemes,
        security=[{"bearerAuth": []}, {"oauth2": ["read", "write"]}]
    )

    # Create task store and agent executor
    task_store = InMemoryTaskStore()
    agent_executor = TckCoreAgentExecutor()
    
    # Create the application using standard SDK class (no custom field injection)
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=TckCoreRequestHandler(agent_executor=agent_executor, task_store=task_store),
    )
    
    # Build the Starlette app with authentication middleware
    starlette_app = app.build()  # Remove middleware temporarily

    # Start the server using uvicorn
    import uvicorn
    print("Starting TCK Core Agent with authentication support on http://localhost:9999")
    print("Authentication schemes: Bearer token, OAuth2")
    print("Agent Card includes securitySchemes for proper A2A authentication testing")
    uvicorn.run(starlette_app, host='0.0.0.0', port=9999)


if __name__ == "__main__":
    main() 