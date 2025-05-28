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
)
from starlette.responses import JSONResponse
from starlette.requests import Request


class TckA2AStarletteApplication(A2AStarletteApplication):
    """Custom A2A application that includes TCK-expected fields in agent card."""
    
    async def _handle_get_agent_card(self, request: Request) -> JSONResponse:
        """Override to include protocolVersion and id fields expected by TCK tests."""
        # Get the standard agent card data
        agent_card_data = self.agent_card.model_dump(mode='json', exclude_none=True)
        
        # Add the missing fields that TCK tests expect
        agent_card_data['protocolVersion'] = '1.0.0'  # A2A protocol version
        agent_card_data['id'] = 'tck-core-agent-id'   # Unique agent identifier
        
        return JSONResponse(agent_card_data)


if __name__ == '__main__':
    skill = AgentSkill(
        id='tck_core_agent',
        name='TCK Core Agent',
        description='A complete A2A agent implementation designed for TCK testing',
        tags=['tck', 'testing', 'core', 'complete'],
        examples=['hi', 'hello world', 'how are you', 'goodbye'],
    )

    # Agent card with task support capabilities
    # Note: Using http://localhost for testing - in production this should be https://
    agent_card = AgentCard(
        name='TCK Core Agent',
        description='A complete A2A agent implementation designed specifically for testing with the A2A Technology Compatibility Kit (TCK)',
        url='http://localhost:9999/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    
    # Set up the custom request handler with task store
    request_handler = TckCoreRequestHandler(
        agent_executor=TckCoreAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # Create the custom A2A server application with TCK-specific agent card handling
    server = TckA2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    import uvicorn

    print("Starting TCK Core Agent on http://localhost:9999")
    print("This agent properly supports:")
    print("- Task creation and management")
    print("- Task state transitions")
    print("- Task cancellation")
    print("- Artifact generation")
    print("- History length limiting")
    print("- Full A2A protocol compliance")
    print("- TCK testing scenarios")
    print("- Additional TCK-expected fields (protocolVersion, id)")
    
    uvicorn.run(server.build(), host='0.0.0.0', port=9999) 