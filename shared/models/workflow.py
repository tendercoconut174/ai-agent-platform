"""Workflow and step models for multi-step task execution."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin, generate_uuid


class Workflow(TimestampMixin, Base):
    """A multi-step workflow triggered by a user request."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | planning | running | completed | failed | cancelled
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(String(20), default="json")
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, default=5)
    callback_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow", order_by="WorkflowStep.created_at", cascade="all, delete-orphan",
    )


class WorkflowStep(TimestampMixin, Base):
    """A single step in a workflow DAG."""

    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflows.id"), index=True,
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # research | analysis | generator | code | monitor | chat
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | running | completed | failed | skipped
    message: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    workflow: Mapped["Workflow"] = relationship(back_populates="steps")
