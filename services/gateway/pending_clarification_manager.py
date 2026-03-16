"""Pending clarification storage – saves and loads human-in-the-loop state.

Falls back to in-memory when PostgreSQL is unavailable.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_memory_pending: dict[str, "PendingClarificationRecord"] = {}
_db_available: Optional[bool] = None


@dataclass
class PendingClarificationRecord:
    """In-memory or DB record for a pending clarification."""

    workflow_id: str
    session_id: Optional[str]
    original_goal: str
    question: str
    output_format: str


def _check_db() -> bool:
    """Check if PostgreSQL is reachable (cached after first check)."""
    global _db_available
    if _db_available is not None:
        return _db_available
    try:
        from sqlalchemy import text
        from database.connection import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_available = True
    except Exception:
        logger.info("PostgreSQL not available – using in-memory pending clarifications")
        _db_available = False
    return _db_available


def save_pending_clarification(
    workflow_id: str,
    session_id: Optional[str],
    original_goal: str,
    question: str,
    output_format: str = "json",
) -> None:
    """Save a pending clarification so the workflow can be resumed later."""
    if not _check_db():
        _memory_pending[workflow_id] = PendingClarificationRecord(
            workflow_id=workflow_id,
            session_id=session_id,
            original_goal=original_goal,
            question=question,
            output_format=output_format,
        )
        return

    from database.connection import SessionLocal
    from shared.models.pending_clarification import PendingClarification

    db = SessionLocal()
    try:
        rec = PendingClarification(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            session_id=session_id,
            original_goal=original_goal,
            question=question,
            output_format=output_format,
        )
        db.add(rec)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Failed to save pending clarification (fallback to memory): %s", e)
        _memory_pending[workflow_id] = PendingClarificationRecord(
            workflow_id=workflow_id,
            session_id=session_id,
            original_goal=original_goal,
            question=question,
            output_format=output_format,
        )
    finally:
        db.close()


def load_and_clear_pending_clarification(
    workflow_id: str,
) -> Optional[PendingClarificationRecord]:
    """Load a pending clarification and remove it. Returns None if not found."""
    if not _check_db():
        return _memory_pending.pop(workflow_id, None)

    from database.connection import SessionLocal
    from shared.models.pending_clarification import PendingClarification

    db = SessionLocal()
    try:
        rec = db.query(PendingClarification).filter(
            PendingClarification.workflow_id == workflow_id,
        ).first()
        if not rec:
            return _memory_pending.pop(workflow_id, None)
        result = PendingClarificationRecord(
            workflow_id=rec.workflow_id,
            session_id=rec.session_id,
            original_goal=rec.original_goal,
            question=rec.question,
            output_format=rec.output_format or "json",
        )
        db.delete(rec)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.warning("Failed to load pending clarification: %s", e)
        return _memory_pending.pop(workflow_id, None)
    finally:
        db.close()
