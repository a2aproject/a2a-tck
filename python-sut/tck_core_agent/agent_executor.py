import asyncio
from typing_extensions import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact
from a2a.utils.errors import ServerError
from a2a.types import TaskNotFoundError, TaskNotCancelableError


class TckCoreAgent:
    """TCK Core Agent that properly supports A2A task workflow."""

    async def invoke(self, query: str) -> str:
        """Process the user query and return a response."""
        if not query.strip():
            return "Hello! Please provide a message for me to respond to."
        
        # Simple responses based on input
        query_lower = query.lower()
        if "hello" in query_lower or "hi" in query_lower:
            return "Hello World! Nice to meet you!"
        elif "how are you" in query_lower:
            return "I'm doing great! Thanks for asking. How can I help you today?"
        elif "goodbye" in query_lower or "bye" in query_lower:
            return "Goodbye! Have a wonderful day!"
        else:
            return f"Hello World! You said: '{query}'. Thanks for your message!"


class TckCoreAgentExecutor(AgentExecutor):
    """Complete AgentExecutor Implementation that properly supports A2A tasks."""

    def __init__(self):
        self.agent = TckCoreAgent()
        self._running_tasks = set()  # Track running tasks

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent with proper task management."""
        query = context.get_user_input()
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')

        # Create task if it doesn't exist (this handles both new tasks and tasks with provided IDs)
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # Check if task is already completed or canceled
        if task.status and task.status.state in [TaskState.completed, TaskState.canceled]:
            # For completed/canceled tasks, just return without doing anything
            return

        # Add task to running tasks
        self._running_tasks.add(task.id)

        try:
            # Update task status to submitted first
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(state=TaskState.submitted),
                    final=False,
                    contextId=task.contextId,
                    taskId=task.id,
                )
            )

            # Short delay to allow tests to see submitted state
            await asyncio.sleep(0.5)

            # Check if task was canceled during delay
            if task.id not in self._running_tasks:
                return  # Task was canceled

            # Update task status to working
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(state=TaskState.working),
                    final=False,
                    contextId=task.contextId,
                    taskId=task.id,
                )
            )

            # Short delay to allow tests to see working state
            await asyncio.sleep(0.5)
            
            # Check for cancellation again
            if task.id not in self._running_tasks:
                return  # Task was canceled
            
            # Process the request
            result = await self.agent.invoke(query)
            await asyncio.sleep(0.2)  # Brief final delay
            
            # Check if task was canceled during processing
            if task.id not in self._running_tasks:
                return  # Task was canceled
            
            # Create an artifact with the result
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    contextId=task.contextId,
                    taskId=task.id,
                    lastChunk=True,
                    artifact=new_text_artifact(
                        name='response',
                        description='Agent response to user message.',
                        text=result,
                    ),
                )
            )

            # Mark task as completed
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(
                        state=TaskState.completed,
                        message=new_agent_text_message(
                            result,
                            task.contextId,
                            task.id,
                        ),
                    ),
                    final=True,
                    contextId=task.contextId,
                    taskId=task.id,
                )
            )

        except Exception as e:
            # Handle errors by marking task as failed
            error_message = f"Error processing request: {str(e)}"
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(
                        state=TaskState.failed,
                        message=new_agent_text_message(
                            error_message,
                            task.contextId,
                            task.id,
                        ),
                    ),
                    final=True,
                    contextId=task.contextId,
                    taskId=task.id,
                )
            )
        finally:
            # Remove task from running tasks
            self._running_tasks.discard(task.id)

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel the task."""
        task = context.current_task
        if not task:
            raise ServerError(TaskNotFoundError(message="No task found to cancel"))
        
        # Check if task is already canceled or completed
        if task.status and task.status.state == TaskState.canceled:
            raise ServerError(TaskNotCancelableError(message="Task is already canceled"))
        
        if task.status and task.status.state == TaskState.completed:
            raise ServerError(TaskNotCancelableError(message="Cannot cancel a completed task"))
        
        # Remove from running tasks to signal cancellation
        self._running_tasks.discard(task.id)
        
        # Cancel the task
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(state=TaskState.canceled),
                final=True,
                contextId=task.contextId,
                taskId=task.id,
            )
        ) 