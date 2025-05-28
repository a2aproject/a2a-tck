"""
Custom request handler for the TCK Core Agent.
"""

from typing_extensions import override
from copy import deepcopy

from a2a.server.context import ServerCallContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import Task, TaskQueryParams
from a2a.utils.errors import ServerError
from a2a.types import TaskNotFoundError


class TckCoreRequestHandler(DefaultRequestHandler):
    """Custom request handler that properly implements historyLength parameter."""

    @override
    async def on_get_task(
        self,
        params: TaskQueryParams,
        context: ServerCallContext | None = None,
    ) -> Task | None:
        """Handler for 'tasks/get' with proper historyLength support."""
        task: Task | None = await self.task_store.get(params.id)
        if not task:
            raise ServerError(error=TaskNotFoundError())
        
        # If historyLength is specified, limit the history
        if params.historyLength is not None and task.history:
            # Create a copy of the task to avoid modifying the stored version
            task_copy = deepcopy(task)
            # Limit history to the most recent N messages
            if len(task_copy.history) > params.historyLength:
                task_copy.history = task_copy.history[-params.historyLength:]
            return task_copy
        
        return task 