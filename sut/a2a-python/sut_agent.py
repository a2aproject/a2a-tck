"""A2A TCK System Under Test (SUT) agent.

Generated from Gherkin scenarios — do not edit by hand.
"""

import asyncio
import logging
import os

import grpc.aio
import uvicorn

from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from starlette.applications import Starlette

import a2a.types.a2a_pb2_grpc as a2a_grpc

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.apps import (
    A2ARESTFastAPIApplication,
    A2AStarletteApplication,
)
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers.default_request_handler import (
    DefaultRequestHandler,
)
from a2a.server.request_handlers.grpc_handler import GrpcHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    Part,
)
from a2a.utils.errors import (
    A2AError,
    TaskNotCancelableError,
    UnsupportedOperationError,
)

REST_URL = '/a2a/rest'

_STREAMING_TIMEOUT_S = 2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TckSutAgent')


class TckAgentExecutor(AgentExecutor):
    """TCK agent executor with messageId-prefix routing."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Execute the agent's logic based on the messageId prefix."""
        task_id = context.task_id
        context_id = context.context_id
        if task_id is None or context_id is None:
            return

        updater = TaskUpdater(event_queue, task_id, context_id)
        message = context.message
        if message is None:
            await updater.complete(
                updater.new_agent_message([Part(text='No message provided')])
            )
            return

        message_id = message.message_id

        if message_id.startswith('tck-stream-artifact-chunked'):
            await updater.start_work()
            await updater.add_artifact(parts=[Part(text="chunk-1 ")], append=True)
            await updater.add_artifact(parts=[Part(text="chunk-2")], append=True, last_chunk=True)
            await updater.complete()
            return

        if message_id.startswith('test-resubscribe-message-id'):
            await updater.start_work()
            await asyncio.sleep(4)
            await updater.complete()
            return

        if message_id.startswith('tck-stream-artifact-text'):
            await updater.start_work()
            await updater.add_artifact(parts=[Part(text="Streamed text content")])
            await updater.complete()
            return

        if message_id.startswith('tck-stream-artifact-file'):
            await updater.start_work()
            await updater.add_artifact(parts=[Part(raw=b'tck', media_type="text/plain", filename="output.txt")])
            await updater.complete()
            return

        if message_id.startswith('tck-stream-ordering-001'):
            await updater.start_work()
            await updater.add_artifact(parts=[Part(text="Ordered output")])
            await updater.complete()
            return

        if message_id.startswith('tck-artifact-file-url'):
            await updater.add_artifact(parts=[Part(url="https://example.com/output.txt", media_type="text/plain", filename="output.txt")])
            await updater.complete()
            return

        if message_id.startswith('tck-message-response'):
            await event_queue.enqueue_event(updater.new_agent_message([Part(text="Direct message response")]))
            return

        if message_id.startswith('tck-input-required'):
            await updater.requires_input()
            return

        if message_id.startswith('tck-complete-task'):
            await updater.complete(updater.new_agent_message([Part(text="Hello from TCK")]))
            return

        if message_id.startswith('tck-artifact-text'):
            await updater.add_artifact(parts=[Part(text="Generated text content")])
            await updater.complete()
            return

        if message_id.startswith('tck-artifact-file'):
            await updater.add_artifact(parts=[Part(raw=b'tck', media_type="text/plain", filename="output.txt")])
            await updater.complete()
            return

        if message_id.startswith('tck-artifact-data'):
            await updater.add_artifact(parts=[Part(data=json_format.Parse("{\"key\": \"value\", \"count\": 42}", Value()))])
            await updater.complete()
            return

        if message_id.startswith('tck-reject-task'):
            raise A2AError('rejected')

        if message_id.startswith('tck-stream-001'):
            await updater.start_work()
            await updater.add_artifact(parts=[Part(text="Stream hello from TCK")])
            await updater.complete()
            return

        if message_id.startswith('tck-stream-002'):
            await updater.complete()
            return

        if message_id.startswith('tck-stream-003'):
            await updater.start_work()
            await updater.add_artifact(parts=[Part(text="Stream task lifecycle")])
            await updater.complete()
            return

        # Default: complete the task with an echo response
        await updater.complete(
            updater.new_agent_message(
                [Part(text='Unhandled messageId prefix: ' + message_id)]
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel a task."""
        task_id = context.task_id
        context_id = context.context_id
        if task_id is None or context_id is None:
            return
        updater = TaskUpdater(event_queue, task_id, context_id)
        await updater.cancel()


def _get_env(name: str, default: str) -> str:
    value = os.environ.get(name, '')
    return value if value else default


async def main() -> None:
    """Start the TCK SUT agent with all three transports."""
    host = _get_env('SUT_HOST', 'localhost:9999')
    http_port = int(host.rsplit(':', 1)[-1]) if ':' in host else 9999
    grpc_port = int(_get_env('GRPC_PORT', str(http_port + 1)))

    agent_card = AgentCard(
        name='A2A TCK SUT',
        description='Auto-generated System Under Test for A2A TCK conformance',
        version='1.0.0',
        provider=AgentProvider(
            organization='A2A Project',
            url='https://github.com/a2aproject',
        ),
        supported_interfaces=[
            AgentInterface(
                url=f'http://{host}',
                protocol_binding='JSONRPC',
                protocol_version='1.0',
            ),
            AgentInterface(
                url=f'http://{host}{REST_URL}',
                protocol_binding='HTTP+JSON',
                protocol_version='1.0',
            ),
            AgentInterface(
                url=f'{host.rsplit(":", 1)[0]}:{grpc_port}',
                protocol_binding='GRPC',
                protocol_version='1.0',
            ),
        ],
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
        ),
        default_input_modes=['text'],
        default_output_modes=['text'],
        skills=[
            AgentSkill(
                id='tck',
                name='TCK Conformance',
                description='Handles TCK conformance test messages',
                tags=['tck'],
            ),
        ],
    )

    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=TckAgentExecutor(),
        task_store=task_store,
    )

    main_app = Starlette()

    # JSON-RPC
    jsonrpc_server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    jsonrpc_server.add_routes_to_app(main_app)

    # REST / HTTP+JSON
    rest_server = A2ARESTFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    rest_app = rest_server.build(rpc_url=REST_URL)
    main_app.mount('', rest_app)

    config = uvicorn.Config(
        main_app, host='0.0.0.0', port=http_port, log_level='info'
    )
    uvicorn_server = uvicorn.Server(config)

    # gRPC
    grpc_server = grpc.aio.server()
    grpc_server.add_insecure_port(f'[::]:{grpc_port}')
    servicer = GrpcHandler(agent_card, request_handler)
    a2a_grpc.add_A2AServiceServicer_to_server(servicer, grpc_server)

    logger.info(
        'Starting HTTP server on port %s and gRPC on port %s...',
        http_port,
        grpc_port,
    )

    await grpc_server.start()
    try:
        await asyncio.gather(
            uvicorn_server.serve(), grpc_server.wait_for_termination()
        )
    finally:
        await grpc_server.stop(0)


if __name__ == '__main__':
    asyncio.run(main())
