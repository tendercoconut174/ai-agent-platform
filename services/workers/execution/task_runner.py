"""Task runner: routes tasks to specialized async agents via the agent registry."""

from typing import Any

from services.agents.registry import get_agent
from shared.models import TaskPayload


async def execute(task: TaskPayload) -> dict[str, Any]:
    """Execute task by routing to the async agent specified in task.agent_type.

    Returns:
        Structured result dict with at least a "result" key.
    """
    agent_fn = get_agent(task.agent_type)
    result_text = await agent_fn(task.message)
    return {"result": result_text, "task_id": task.task_id}
