"""Scheduler agent – infers schedule from user prompts and schedules tasks for future execution."""

import logging
import time
from datetime import datetime, timezone

from services.agents.base_agent import create_react_agent
from shared.llm import is_llm_available

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a scheduler agent. Your job is to schedule tasks for future execution based on user requests.\n\n"
    "You MUST use tool_schedule_task when the user asks to:\n"
    "- Schedule, remind, run later, run tomorrow, run at X time\n"
    "- Run daily, run every hour, run weekly, run every day\n"
    "- Run every X minutes, talk to me every X minutes, notify me every X seconds (→ every_1_minute)\n"
    "- Set a reminder, create a recurring task\n\n"
    "The message includes current UTC time. Infer and pass:\n"
    "1. task_description: What to run (e.g. 'research top tech news', 'chat with me')\n"
    "2. next_run_at: ISO 8601 datetime (e.g. 2025-03-18T14:05:00Z). Compute from user intent:\n"
    "   - 'in 5 minutes' → now + 5 min\n"
    "   - 'tomorrow at 9am' → next day 09:00 UTC\n"
    "   - 'every 5 minutes' → now + 5 min (first run)\n"
    "3. recurrence: 'once', 'hourly', 'daily', 'weekly', or 'every_N_minutes' (e.g. every_5_minutes). "
    "'every X seconds' → every_1_minute (platform minimum).\n\n"
    "Use tool_list_scheduled_tasks when the user asks what's scheduled or to list tasks.\n"
    "Use tool_cancel_scheduled_task when the user asks to cancel or remove a scheduled task (you need the task_id).\n\n"
    "Always call the appropriate tool. Never respond without calling a tool for scheduling requests."
)

_agent = create_react_agent("scheduler", SYSTEM_PROMPT)


async def run(message: str) -> str:
    t0 = time.perf_counter()
    logger.info("[scheduler] START | msg_len=%d", len(message))

    if not is_llm_available("agents"):
        logger.warning("[scheduler] No LLM configured")
        return (
            "[scheduler] No LLM API key configured. "
            "Scheduling requires an LLM to parse your request. Message: " + message
        )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg_with_time = f"Current UTC time: {now}\n\nUser request: {message}"
    try:
        result = await _agent(msg_with_time)
        logger.info("[scheduler] DONE | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
        return result
    except Exception as e:
        logger.exception("[scheduler] FAILED | %.2fs: %s", time.perf_counter() - t0, e)
        raise


__all__ = ["run"]
