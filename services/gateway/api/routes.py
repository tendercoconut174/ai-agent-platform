import uuid

from fastapi import APIRouter
from platform_queue.task_queue import enqueue_task, wait_for_result

router = APIRouter()

@router.post("/message")
def message(payload: dict):
    task_id = str(uuid.uuid4())
    task = {"task_id": task_id, **payload}
    enqueue_task(task)
    result = wait_for_result(task_id)
    if result is None:
        return {"status": "timeout", "task_id": task_id}
    return result