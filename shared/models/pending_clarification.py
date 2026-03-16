"""Pending clarification model for human-in-the-loop."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TimestampMixin, generate_uuid


class PendingClarification(TimestampMixin, Base):
    """Stores a workflow paused for user clarification."""

    __tablename__ = "pending_clarifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    original_goal: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(String(20), nullable=False, default="json")
