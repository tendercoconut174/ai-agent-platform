"""Session and message history models."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin, generate_uuid


class Session(TimestampMixin, Base):
    """Conversation session with a user."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    messages: Mapped[list["MessageHistory"]] = relationship(
        back_populates="session", order_by="MessageHistory.created_at", cascade="all, delete-orphan",
    )


class MessageHistory(TimestampMixin, Base):
    """Individual message in a conversation session."""

    __tablename__ = "message_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text")  # text, audio, image, file
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="messages")
