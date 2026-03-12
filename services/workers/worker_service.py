"""Worker service that consumes tasks from Redis and executes agents."""

import json
import os

import redis
from dotenv import load_dotenv

load_dotenv()

from services.workers.execution.task_runner import execute
from shared.models import TaskPayload

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)

while True:
    _, task_json = redis_client.brpop("task_queue")
    data = json.loads(task_json)
    task = TaskPayload.model_validate(data)

    print("Processing task:", task.model_dump())

    result = execute(task)

    print("Result:", result)

    redis_client.rpush(f"result:{task.task_id}", json.dumps(result))
