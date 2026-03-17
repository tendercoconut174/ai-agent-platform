"""Scheduler service – runs due tasks by calling the orchestrator."""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")
SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))


def _get_db_session():
    try:
        from database.connection import SessionLocal

        return SessionLocal()
    except Exception as e:
        logger.warning("[scheduler] DB unavailable: %s", e)
        return None


def _compute_next_run(current: datetime, recurrence: str) -> datetime:
    """Compute next run time for recurring tasks."""
    if recurrence == "hourly":
        return current + timedelta(hours=1)
    if recurrence == "daily":
        return current + timedelta(days=1)
    if recurrence == "weekly":
        return current + timedelta(days=7)
    # every_N_minutes (e.g. every_5_minutes, every_1_minute)
    if recurrence.startswith("every_") and ("_minutes" in recurrence or "_minute" in recurrence):
        try:
            n = int(recurrence.replace("every_", "").replace("_minutes", "").replace("_minute", ""))
            return current + timedelta(minutes=max(1, min(n, 60)))
        except ValueError:
            pass
    return current  # once – no next run


async def _execute_task(message: str) -> tuple[bool, str]:
    """Execute a task by calling the orchestrator. Returns (success, result_or_error)."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json={
                    "message": message,
                    "output_format": "json",
                    "mode": "auto",
                    "conversation_history": [],
                    "format_hint": "",
                    "is_clarification_resume": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", "")
            if data.get("needs_clarification"):
                return False, "Task needs clarification: " + (data.get("question") or result)
            if data.get("needs_code_approval"):
                return False, "Task requires code approval; cannot run unattended."
            return True, result
    except httpx.HTTPStatusError as e:
        return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return False, str(e)


async def _run_due_tasks() -> None:
    """Fetch due tasks and execute each via orchestrator."""
    db = _get_db_session()
    if not db:
        logger.warning("[scheduler] Database unavailable – cannot run due tasks")
        return

    try:
        from shared.models.scheduled_task import ScheduledTask

        now = datetime.now(timezone.utc)
        due = (
            db.query(ScheduledTask)
            .filter(
                ScheduledTask.status == "pending",
                ScheduledTask.next_run_at <= now,
            )
            .all()
        )

        if not due:
            logger.debug("[scheduler] No due tasks")
        for task in due:
            task.status = "running"
            db.commit()

            success, result_or_error = await _execute_task(task.message)

            task.run_count += 1
            task.last_run_at = now
            if success:
                task.last_error = None
                if task.recurrence == "once":
                    task.status = "completed"
                else:
                    task.status = "pending"
                    task.next_run_at = _compute_next_run(now, task.recurrence)
                logger.info("[scheduler] Task %s executed | recurrence=%s | next=%s",
                            task.id, task.recurrence, task.next_run_at if task.recurrence != "once" else "done")
            else:
                task.status = "failed"
                task.last_error = (result_or_error or "")[:500]
                logger.warning("[scheduler] Task %s failed: %s", task.id, (result_or_error or "")[:200])

            db.commit()

    except Exception as e:
        logger.exception("[scheduler] Error running due tasks: %s", e)
        db.rollback()
    finally:
        db.close()


async def run_scheduler_loop() -> None:
    """Main scheduler loop – checks for due tasks every SCHEDULER_INTERVAL_SECONDS."""
    logger.info("[scheduler] Starting scheduler loop | interval=%ds | orchestrator=%s",
                SCHEDULER_INTERVAL_SECONDS, ORCHESTRATOR_URL)

    # Verify DB and orchestrator at startup
    db = _get_db_session()
    if db:
        try:
            from shared.models.scheduled_task import ScheduledTask
            pending = db.query(ScheduledTask).filter(ScheduledTask.status == "pending").count()
            logger.info("[scheduler] DB OK | %d pending tasks", pending)
        except Exception as e:
            logger.warning("[scheduler] DB check failed: %s", e)
        finally:
            db.close()
    else:
        logger.warning("[scheduler] DB unavailable – scheduler will not run tasks")

    while True:
        try:
            await _run_due_tasks()
        except Exception as e:
            logger.exception("[scheduler] Loop error: %s", e)
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)


def main() -> None:
    """Entry point for scheduler service."""
    from shared.logging_config import setup_logging

    setup_logging()
    asyncio.run(run_scheduler_loop())


if __name__ == "__main__":
    main()
