"""Worker service – consumes tasks from Redis Streams and executes async agents."""

import asyncio
import logging
import signal
import traceback

from dotenv import load_dotenv

load_dotenv()

from platform_queue.task_queue import ack_task, consume_task, publish_progress, push_result
from services.agents.registry import get_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("worker")

_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    logger.info("Shutdown signal received")
    _shutdown = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


async def main():
    logger.info("Worker starting...")
    while not _shutdown:
        item = consume_task(block_ms=5000)
        if item is None:
            continue

        msg_id, task = item
        task_id = task.get("task_id", "unknown")
        workflow_id = task.get("workflow_id", "")
        agent_type = task.get("agent_type", "research")
        message = task.get("message", "")

        logger.info("Processing task %s (agent=%s, workflow=%s)", task_id, agent_type, workflow_id)

        publish_progress(workflow_id, {
            "task_id": task_id, "agent_type": agent_type, "status": "running",
        })

        try:
            agent_fn = get_agent(agent_type)
            result_text = await agent_fn(message)
            result = {"result": result_text, "error": None}
            logger.info("Task %s completed (%d chars)", task_id, len(result_text))
        except Exception as e:
            logger.exception("Task %s failed: %s", task_id, e)
            result = {"result": "", "error": traceback.format_exc()}

        push_result(task_id, result)
        ack_task(msg_id)

        publish_progress(workflow_id, {
            "task_id": task_id, "agent_type": agent_type, "status": "completed" if not result.get("error") else "failed",
        })

    logger.info("Worker shut down")


if __name__ == "__main__":
    asyncio.run(main())
