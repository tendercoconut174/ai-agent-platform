"""Task runner: routes tasks to specialized async agents via the agent registry."""

import logging
import time
from typing import Any

from services.agents.registry import get_agent
from shared.models import TaskPayload

logger = logging.getLogger(__name__)


async def execute(task: TaskPayload) -> dict[str, Any]:
    """Execute task by routing to the async agent specified in task.agent_type.

    Returns:
        Structured result dict with at least a "result" key.
    """
    t0 = time.perf_counter()
    logger.info("[task_runner] execute | task_id=%s | agent_type=%s", task.task_id, task.agent_type)
    agent_fn = get_agent(task.agent_type)
    result_text = await agent_fn(task.message)
    logger.info("[task_runner] DONE | task_id=%s | result_len=%d | %.2fs", task.task_id, len(result_text), time.perf_counter() - t0)
    return {"result": result_text, "task_id": task.task_id}
