"""Pending code approval model for human-in-the-loop code execution."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TimestampMixin, generate_uuid


class PendingCodeApproval(TimestampMixin, Base):
    """Stores a workflow paused for user approval of code execution."""

    __tablename__ = "pending_code_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    original_goal: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(String(20), nullable=False, default="json")
