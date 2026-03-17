"""Redis Streams-based task queue for reliable message delivery."""

import json
import logging
import os
import time
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

TASK_STREAM = "task_stream"
RESULT_PREFIX = "result:"
CONSUMER_GROUP = "workers"
CONSUMER_NAME = f"worker-{os.getpid()}"


def _ensure_consumer_group():
    """Create consumer group if it doesn't exist."""
    try:
        redis_client.xgroup_create(TASK_STREAM, CONSUMER_GROUP, id="0", mkstream=True)
        logger.debug("[task_queue] Created consumer group %s", CONSUMER_GROUP)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            logger.warning("[task_queue] Consumer group creation failed: %s", e)
            raise


def enqueue_task(task: dict[str, Any]) -> str:
    """Add a task to the stream.

    Args:
        task: Task dict with task_id, workflow_id, agent_type, message, etc.

    Returns:
        Stream message ID.
    """
    _ensure_consumer_group()
    msg_id = redis_client.xadd(TASK_STREAM, {"data": json.dumps(task)})
    logger.info("[task_queue] enqueue_task | task_id=%s | msg_id=%s", task.get("task_id", "?"), msg_id)
    return msg_id


def consume_task(block_ms: int = 5000) -> Optional[tuple[str, dict[str, Any]]]:
    """Read next task from the stream (blocking).

    Args:
        block_ms: Milliseconds to block waiting for messages.

    Returns:
        Tuple of (stream_msg_id, task_dict) or None on timeout.
    """
    _ensure_consumer_group()
    results = redis_client.xreadgroup(
        CONSUMER_GROUP, CONSUMER_NAME, {TASK_STREAM: ">"}, count=1, block=block_ms,
    )
    if not results:
        return None
    stream_name, messages = results[0]
    if not messages:
        return None
    msg_id, fields = messages[0]
    task = json.loads(fields["data"])
    logger.debug("[task_queue] consume_task | msg_id=%s | task_id=%s", msg_id, task.get("task_id", "?"))
    return (msg_id, task)


def ack_task(msg_id: str):
    """Acknowledge a processed task."""
    redis_client.xack(TASK_STREAM, CONSUMER_GROUP, msg_id)
    logger.debug("[task_queue] ack_task | msg_id=%s", msg_id)


def push_result(task_id: str, result: dict[str, Any], ttl: int = 3600):
    """Push result for a task, with TTL."""
    key = f"{RESULT_PREFIX}{task_id}"
    redis_client.rpush(key, json.dumps(result))
    redis_client.expire(key, ttl)
    logger.info("[task_queue] push_result | task_id=%s", task_id)


def wait_for_result(task_id: str, timeout: int = 60) -> Optional[dict[str, Any]]:
    """Block until a result is available.

    Args:
        task_id: Task identifier.
        timeout: Max seconds to wait.

    Returns:
        Result dict or None on timeout.
    """
    key = f"{RESULT_PREFIX}{task_id}"
    popped = redis_client.brpop(key, timeout=timeout)
    if popped is None:
        logger.debug("[task_queue] wait_for_result timeout | task_id=%s", task_id)
        return None
    _, result_json = popped
    logger.debug("[task_queue] wait_for_result got result | task_id=%s", task_id)
    return json.loads(result_json)


def publish_progress(workflow_id: str, data: dict[str, Any]):
    """Publish progress update via Redis Pub/Sub for SSE streaming."""
    redis_client.publish(f"progress:{workflow_id}", json.dumps(data))
