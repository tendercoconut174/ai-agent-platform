"""Redis task queue for gateway-worker communication."""

import json
import os
from typing import Any, Dict, Optional

import redis

from shared.models import TaskPayload

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)


def enqueue_task(task: TaskPayload) -> str:
    """Enqueue task and return task_id.

    Args:
        task: Task payload with task_id and message.

    Returns:
        The task_id for result retrieval.
    """
    redis_client.lpush("task_queue", task.model_dump_json())
    return task.task_id


def wait_for_result(task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Block until worker returns result or timeout.

    Args:
        task_id: Unique task identifier.
        timeout: Seconds to wait before returning None.

    Returns:
        Result dict from worker, or None on timeout.
    """
    result_key = f"result:{task_id}"
    _, result_json = redis_client.brpop(result_key, timeout=timeout)
    if result_json is None:
        return None
    return json.loads(result_json)
