"""Pending code approval storage – saves and loads human-in-the-loop code execution state.

Falls back to in-memory when PostgreSQL is unavailable.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_memory_pending: dict[str, "PendingCodeApprovalRecord"] = {}
_db_available: Optional[bool] = None


@dataclass
class PendingCodeApprovalRecord:
    """In-memory or DB record for a pending code approval."""

    approval_id: str
    workflow_id: str
    session_id: Optional[str]
    code: str
    step_id: str
    original_goal: str
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
        logger.info("PostgreSQL not available – using in-memory pending code approvals")
        _db_available = False
    return _db_available


def save_pending_code_approval(
    workflow_id: str,
    session_id: Optional[str],
    code: str,
    step_id: str,
    original_goal: str,
    output_format: str = "json",
) -> str:
    """Save a pending code approval. Returns approval_id."""
    approval_id = str(uuid.uuid4())
    record = PendingCodeApprovalRecord(
        approval_id=approval_id,
        workflow_id=workflow_id,
        session_id=session_id,
        code=code,
        step_id=step_id,
        original_goal=original_goal,
        output_format=output_format,
    )

    if not _check_db():
        _memory_pending[approval_id] = record
        return approval_id

    from database.connection import SessionLocal
    from shared.models.pending_code_approval import PendingCodeApproval

    db = SessionLocal()
    try:
        rec = PendingCodeApproval(
            id=approval_id,
            workflow_id=workflow_id,
            session_id=session_id,
            code=code,
            step_id=step_id,
            original_goal=original_goal,
            output_format=output_format,
        )
        db.add(rec)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Failed to save pending code approval (fallback to memory): %s", e)
        _memory_pending[approval_id] = record
    finally:
        db.close()

    return approval_id


def save_pending_code_approval_by_id(
    approval_id: str,
    workflow_id: str,
    session_id: Optional[str],
    code: str,
    step_id: str,
    original_goal: str,
    output_format: str = "json",
) -> None:
    """Save a pending code approval with a given ID. Used by gateway when it receives
    the pending from orchestrator stream (gateway and orchestrator are separate processes,
    so in-memory storage is not shared; gateway must save locally when it receives the event)."""
    record = PendingCodeApprovalRecord(
        approval_id=approval_id,
        workflow_id=workflow_id,
        session_id=session_id,
        code=code,
        step_id=step_id,
        original_goal=original_goal,
        output_format=output_format,
    )
    if not _check_db():
        _memory_pending[approval_id] = record
        return
    from database.connection import SessionLocal
    from shared.models.pending_code_approval import PendingCodeApproval

    db = SessionLocal()
    try:
        rec = PendingCodeApproval(
            id=approval_id,
            workflow_id=workflow_id,
            session_id=session_id,
            code=code,
            step_id=step_id,
            original_goal=original_goal,
            output_format=output_format,
        )
        db.add(rec)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Failed to save pending code approval by id (fallback to memory): %s", e)
        _memory_pending[approval_id] = record
    finally:
        db.close()


def load_and_clear_pending_code_approval(approval_id: str) -> Optional[PendingCodeApprovalRecord]:
    """Load a pending code approval and remove it. Returns None if not found."""
    if not _check_db():
        return _memory_pending.pop(approval_id, None)

    from database.connection import SessionLocal
    from shared.models.pending_code_approval import PendingCodeApproval

    db = SessionLocal()
    try:
        rec = db.query(PendingCodeApproval).filter(PendingCodeApproval.id == approval_id).first()
        if not rec:
            return _memory_pending.pop(approval_id, None)
        result = PendingCodeApprovalRecord(
            approval_id=rec.id,
            workflow_id=rec.workflow_id,
            session_id=rec.session_id,
            code=rec.code,
            step_id=rec.step_id,
            original_goal=rec.original_goal,
            output_format=rec.output_format or "json",
        )
        db.delete(rec)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.warning("Failed to load pending code approval: %s", e)
        return _memory_pending.pop(approval_id, None)
    finally:
        db.close()
