"""Task runner: routes tasks to specialized agents based on task_type."""

from typing import Any, Callable, Dict

from shared.models import TaskPayload

from services.workers.agents.general_agent import run_general_agent
from services.workers.agents.research_agent import run_research_agent

# Registry of task_type -> agent runner
AGENT_REGISTRY: Dict[str, Callable[[str], Any]] = {
    "research": run_research_agent,
    "summarize": run_research_agent,  # Reuse research for now; add summarize_agent later
    "general": run_general_agent,
}


def execute(task: TaskPayload) -> Dict[str, Any]:
    """Execute task by routing to specialized agent based on task_type.

    Args:
        task: Task payload with task_id, message, and task_type.

    Returns:
        Structured result dict from the agent.
    """
    agent_fn = AGENT_REGISTRY.get(task.task_type)
    if agent_fn:
        result = agent_fn(task.message)
        return result.model_dump()
    # Fallback: try research if message contains "research"
    if "research" in task.message:
        result = run_research_agent(task.message)
        return result.model_dump()
    # Fallback: use general agent for any other task
    result = run_general_agent(task.message)
    return result.model_dump()
