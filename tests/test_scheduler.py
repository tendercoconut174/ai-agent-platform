"""Tests for scheduler tool, agent, and service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.scheduler.scheduler_service import _compute_next_run
from shared.mcp.tools.scheduler import (
    _parse_iso_datetime,
    tool_cancel_scheduled_task,
    tool_list_scheduled_tasks,
    tool_schedule_task,
)


class TestParseIsoDatetime:
    """Tests for ISO datetime parsing."""

    def test_parses_iso_with_z(self) -> None:
        """Parse ISO format with Z suffix."""
        dt = _parse_iso_datetime("2025-03-18T14:05:00Z")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 18
        assert dt.hour == 14
        assert dt.minute == 5

    def test_parses_iso_with_offset(self) -> None:
        """Parse ISO format with +00:00 offset."""
        dt = _parse_iso_datetime("2025-03-18T14:05:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_returns_none_for_invalid(self) -> None:
        """Invalid string returns None."""
        assert _parse_iso_datetime("not a date") is None
        assert _parse_iso_datetime("") is None
        assert _parse_iso_datetime(None) is None


class TestToolScheduleTask:
    """Tests for tool_schedule_task."""

    @patch("shared.mcp.tools.scheduler._get_db_session")
    def test_invalid_next_run_at_returns_error(self, mock_db: MagicMock) -> None:
        """Invalid next_run_at returns error message."""
        mock_db.return_value = MagicMock()
        result = tool_schedule_task.invoke({
            "task_description": "check weather",
            "next_run_at": "invalid",
            "recurrence": "once",
        })
        assert "Invalid" in result
        assert "ISO 8601" in result

    @patch("shared.mcp.tools.scheduler._get_db_session")
    def test_no_db_returns_unavailable(self, mock_db: MagicMock) -> None:
        """When DB unavailable, returns unavailable message."""
        mock_db.return_value = None
        result = tool_schedule_task.invoke({
            "task_description": "check weather",
            "next_run_at": "2025-03-18T14:05:00Z",
            "recurrence": "once",
        })
        assert "unavailable" in result.lower() or "not configured" in result.lower()

    @patch("shared.mcp.tools.scheduler._get_db_session")
    @patch("shared.models.scheduled_task.ScheduledTask")
    def test_valid_schedule_creates_task(
        self, mock_scheduled_task_cls: MagicMock, mock_db: MagicMock
    ) -> None:
        """Valid schedule creates task and returns confirmation."""
        mock_session = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_scheduled_task_cls.return_value = mock_task
        mock_db.return_value = mock_session

        result = tool_schedule_task.invoke({
            "task_description": "check weather",
            "next_run_at": "2025-03-18T14:05:00Z",
            "recurrence": "once",
        })

        assert "Scheduled" in result or "task" in result
        mock_scheduled_task_cls.assert_called_once()
        mock_session.add.assert_called_once_with(mock_task)
        mock_session.commit.assert_called()


class TestToolListScheduledTasks:
    """Tests for tool_list_scheduled_tasks."""

    @patch("shared.mcp.tools.scheduler._get_db_session")
    def test_no_db_returns_unavailable(self, mock_db: MagicMock) -> None:
        """When DB unavailable, returns unavailable message."""
        mock_db.return_value = None
        result = tool_list_scheduled_tasks.invoke({})
        assert "not available" in result.lower() or "database" in result.lower()


class TestToolCancelScheduledTask:
    """Tests for tool_cancel_scheduled_task."""

    @patch("shared.mcp.tools.scheduler._get_db_session")
    def test_no_db_returns_unavailable(self, mock_db: MagicMock) -> None:
        """When DB unavailable, returns unavailable message."""
        mock_db.return_value = None
        result = tool_cancel_scheduled_task.invoke({"task_id": "task-123"})
        assert "not available" in result.lower() or "database" in result.lower()


class TestSchedulerAgent:
    """Tests for scheduler agent."""

    @pytest.mark.asyncio
    @patch("services.agents.scheduler_agent.is_llm_available")
    async def test_no_llm_returns_fallback(self, mock_available: MagicMock) -> None:
        """When LLM not available, returns fallback message."""
        mock_available.return_value = False
        from services.agents import scheduler_agent

        result = await scheduler_agent.run("remind me in 5 minutes to check weather")
        assert "No LLM" in result or "API key" in result

    @pytest.mark.asyncio
    @patch("services.agents.scheduler_agent.create_react_agent")
    async def test_with_llm_returns_string(self, mock_factory: MagicMock) -> None:
        """With LLM, returns string from agent."""
        mock_agent = AsyncMock(return_value="Scheduled task 'check weather' for 2025-03-18 14:10 UTC.")
        mock_factory.return_value = mock_agent

        with patch("services.agents.scheduler_agent.is_llm_available", return_value=True):
            from services.agents import scheduler_agent

            result = await scheduler_agent.run("remind me in 5 minutes to check weather")
        assert isinstance(result, str)
        assert "Scheduled" in result or "task" in result


class TestSchedulerServiceComputeNextRun:
    """Tests for _compute_next_run in scheduler service."""

    def test_hourly_adds_one_hour(self) -> None:
        """Hourly recurrence adds 1 hour."""
        now = datetime(2025, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        next_run = _compute_next_run(now, "hourly")
        assert next_run == now + timedelta(hours=1)

    def test_daily_adds_one_day(self) -> None:
        """Daily recurrence adds 1 day."""
        now = datetime(2025, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        next_run = _compute_next_run(now, "daily")
        assert next_run == now + timedelta(days=1)

    def test_weekly_adds_seven_days(self) -> None:
        """Weekly recurrence adds 7 days."""
        now = datetime(2025, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        next_run = _compute_next_run(now, "weekly")
        assert next_run == now + timedelta(days=7)

    def test_every_5_minutes_adds_five_minutes(self) -> None:
        """every_5_minutes adds 5 minutes."""
        now = datetime(2025, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        next_run = _compute_next_run(now, "every_5_minutes")
        assert next_run == now + timedelta(minutes=5)

    def test_every_1_minute_adds_one_minute(self) -> None:
        """every_1_minute adds 1 minute."""
        now = datetime(2025, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        next_run = _compute_next_run(now, "every_1_minute")
        assert next_run == now + timedelta(minutes=1)

    def test_once_returns_same_time(self) -> None:
        """Once recurrence returns same time (no next run)."""
        now = datetime(2025, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        next_run = _compute_next_run(now, "once")
        assert next_run == now
