"""Session manager – creates/retrieves sessions and stores message history.

Falls back to in-memory storage when PostgreSQL is unavailable.
"""

import logging
import uuid
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory fallback when PostgreSQL is not available
_memory_sessions: dict[str, bool] = {}
_memory_messages: dict[str, list[dict[str, str]]] = defaultdict(list)
_db_available: Optional[bool] = None


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
        logger.info("PostgreSQL not available – using in-memory session storage")
        _db_available = False
    return _db_available


def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, bool]:
    """Get existing session or create a new one.

    Returns:
        Tuple of (session_id, created).
    """
    if not _check_db():
        if session_id and session_id in _memory_sessions:
            return session_id, False
        sid = session_id or str(uuid.uuid4())
        _memory_sessions[sid] = True
        return sid, True

    from database.connection import SessionLocal
    from shared.models.session import Session

    db = SessionLocal()
    try:
        if session_id:
            session = db.query(Session).filter(Session.id == session_id, Session.is_active == True).first()
            if session:
                return session.id, False
        session = Session()
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id, True
    except Exception as e:
        db.rollback()
        logger.warning("Session DB error (falling back): %s", e)
        sid = session_id or str(uuid.uuid4())
        _memory_sessions[sid] = True
        return sid, True
    finally:
        db.close()


def add_message(session_id: str, role: str, content: str, content_type: str = "text"):
    """Store a message in session history."""
    if not _check_db():
        _memory_messages[session_id].append({"role": role, "content": content[:50000]})
        return

    from database.connection import SessionLocal
    from shared.models.session import MessageHistory

    db = SessionLocal()
    try:
        msg = MessageHistory(
            session_id=session_id, role=role,
            content=content[:50000], content_type=content_type,
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        _memory_messages[session_id].append({"role": role, "content": content[:50000]})
        logger.debug("Stored message in memory (DB unavailable): %s", e)
    finally:
        db.close()


def get_history(session_id: str, limit: int = 20) -> list[dict[str, str]]:
    """Get recent message history for a session."""
    if not _check_db():
        msgs = _memory_messages.get(session_id, [])
        return msgs[-limit:]

    from database.connection import SessionLocal
    from shared.models.session import MessageHistory

    db = SessionLocal()
    try:
        messages = (
            db.query(MessageHistory)
            .filter(MessageHistory.session_id == session_id)
            .order_by(MessageHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]
    except Exception as e:
        logger.debug("History fallback to memory: %s", e)
        msgs = _memory_messages.get(session_id, [])
        return msgs[-limit:]
    finally:
        db.close()
