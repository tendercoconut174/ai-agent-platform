import redis
import json

from services.workers.execution.task_runner import execute

redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

while True:

    _, task = redis_client.brpop("task_queue")

    data = json.loads(task)

    print("Processing task:", data)

    result = execute(data)

    print("Result:", result)

    task_id = data.get("task_id")
    if task_id:
        redis_client.rpush(f"result:{task_id}", json.dumps(result))