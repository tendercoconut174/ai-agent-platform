import redis
import json

redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

def enqueue_task(task: dict) -> str:
    """Enqueue task and return task_id. Task must include 'task_id' key."""
    redis_client.lpush("task_queue", json.dumps(task))
    return task["task_id"]

def wait_for_result(task_id: str, timeout: int = 30) -> dict | None:
    """Block until worker returns result or timeout. Returns result dict or None."""
    result_key = f"result:{task_id}"
    _, result_json = redis_client.brpop(result_key, timeout=timeout)
    if result_json is None:
        return None
    return json.loads(result_json)
