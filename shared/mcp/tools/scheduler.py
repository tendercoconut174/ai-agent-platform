"""Scheduler tool – schedule tasks for future execution.

Schedule inference is LLM-driven: the agent infers next_run_at and recurrence from the user message.
No hardcoded parsing; the tool accepts structured values from the LLM.
"""

import logging
from datetime import datetime, timezone

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_db_session():
    """Get a sync database session. Falls back to in-memory if DB unavailable."""
    try:
        from database.connection import SessionLocal

        return SessionLocal()
    except Exception as e:
        logger.warning("[scheduler] DB unavailable: %s", e)
        return None


def _parse_iso_datetime(s: str) -> datetime | None:
    """Parse ISO 8601 datetime from LLM output. Returns None if invalid. Deserialization only – no inference."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


@tool
def tool_schedule_task(
    task_description: str,
    next_run_at: str,
    recurrence: str = "once",
) -> str:
    """Schedule a task for future execution.

    Use when the user asks to schedule, remind, run later, run daily, run every hour, etc.
    You MUST infer next_run_at and recurrence from the user message. Current UTC time is provided in the message.

    Args:
        task_description: What to run (e.g. 'research top tech news', 'chat with me', 'send me a summary').
        next_run_at: ISO 8601 datetime for first run (e.g. 2025-03-18T14:05:00Z). Compute from user intent:
            'in 5 minutes' = now + 5 min; 'tomorrow at 9am' = next day 09:00 UTC; 'every 5 minutes' = now + 5 min.
        recurrence: 'once', 'hourly', 'daily', 'weekly', or 'every_N_minutes' (e.g. every_5_minutes).
            For 'every X seconds' use every_1_minute (platform minimum). For 'every X minutes' use every_N_minutes.

    Returns:
        Confirmation message with task ID and next run time.
    """
    next_run = _parse_iso_datetime(next_run_at)
    if next_run is None:
        return (
            f"Invalid next_run_at: '{next_run_at}'. "
            "Provide ISO 8601 format (e.g. 2025-03-18T14:05:00Z). Current UTC time is in the message."
        )

    db = _get_db_session()
    if not db:
        return (
            "Scheduling is unavailable (database not configured). "
            "Tasks can only run immediately in this environment."
        )

    try:
        from shared.models.scheduled_task import ScheduledTask

        task = ScheduledTask(
            message=task_description,
            next_run_at=next_run,
            recurrence=recurrence,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info("[scheduler] Scheduled task %s | run_at=%s | recurrence=%s", task.id, next_run, recurrence)
        desc = task_description[:80] + "..." if len(task_description) > 80 else task_description
        return (
            f"Scheduled task '{desc}' "
            f"for {next_run.strftime('%Y-%m-%d %H:%M UTC')} "
            f"(recurrence: {recurrence}). Task ID: {task.id}. "
            f"The scheduler service will execute it when due."
        )
    except Exception as e:
        logger.exception("[scheduler] Failed to schedule: %s", e)
        db.rollback()
        return f"Failed to schedule task: {e}"
    finally:
        db.close()


@tool
def tool_list_scheduled_tasks() -> str:
    """List all pending scheduled tasks. Use when the user asks what's scheduled or to list tasks."""
    db = _get_db_session()
    if not db:
        return "Database not available. No scheduled tasks to list."

    try:
        from shared.models.scheduled_task import ScheduledTask

        tasks = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.status == "pending")
            .order_by(ScheduledTask.next_run_at)
            .limit(20)
            .all()
        )
        if not tasks:
            return "No pending scheduled tasks."
        lines = []
        for t in tasks:
            lines.append(
                f"- {t.id}: {t.message[:60]}... | {t.next_run_at.strftime('%Y-%m-%d %H:%M')} | {t.recurrence}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.exception("[scheduler] Failed to list: %s", e)
        return f"Failed to list tasks: {e}"
    finally:
        db.close()


@tool
def tool_cancel_scheduled_task(task_id: str) -> str:
    """Cancel a scheduled task by ID. Use when the user asks to cancel or remove a scheduled task."""
    db = _get_db_session()
    if not db:
        return "Database not available. Cannot cancel tasks."

    try:
        from shared.models.scheduled_task import ScheduledTask

        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return f"Task {task_id} not found."
        if task.status != "pending":
            return f"Task {task_id} is already {task.status}, cannot cancel."
        task.status = "cancelled"
        db.commit()
        logger.info("[scheduler] Cancelled task %s", task_id)
        return f"Cancelled scheduled task {task_id}."
    except Exception as e:
        logger.exception("[scheduler] Failed to cancel: %s", e)
        db.rollback()
        return f"Failed to cancel: {e}"
    finally:
        db.close()
