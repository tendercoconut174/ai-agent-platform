"""add scheduled_tasks table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-17 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recurrence", sa.String(length=20), nullable=False, server_default="once"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduled_tasks_status"), "scheduled_tasks", ["status"])
    op.create_index(op.f("ix_scheduled_tasks_next_run_at"), "scheduled_tasks", ["next_run_at"])
    op.create_index(op.f("ix_scheduled_tasks_session_id"), "scheduled_tasks", ["session_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_tasks_session_id"), table_name="scheduled_tasks")
    op.drop_index(op.f("ix_scheduled_tasks_next_run_at"), table_name="scheduled_tasks")
    op.drop_index(op.f("ix_scheduled_tasks_status"), table_name="scheduled_tasks")
    op.drop_table("scheduled_tasks")
