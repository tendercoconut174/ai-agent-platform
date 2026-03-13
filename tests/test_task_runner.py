"""Unit tests for async task runner."""

from unittest.mock import AsyncMock, patch

import pytest

from services.workers.execution.task_runner import execute
from shared.models import TaskPayload


def _make_task(agent_type: str = "research", message: str = "test") -> TaskPayload:
    return TaskPayload(
        task_id="t1",
        workflow_id="wf-1",
        step_id="step-1",
        agent_type=agent_type,
        message=message,
    )


class TestExecute:
    """Tests for async execute function."""

    @pytest.mark.asyncio
    @patch("services.workers.execution.task_runner.get_agent")
    async def test_research_task_routes_to_agent(self, mock_get) -> None:
        mock_get.return_value = AsyncMock(return_value="Researched: research AI")
        task = _make_task(agent_type="research", message="research AI")
        result = await execute(task)
        mock_get.assert_called_once_with("research")
        assert "Researched: research AI" == result["result"]

    @pytest.mark.asyncio
    @patch("services.workers.execution.task_runner.get_agent")
    async def test_analysis_task_routes_to_agent(self, mock_get) -> None:
        mock_get.return_value = AsyncMock(return_value="Analyzed: AI trends")
        task = _make_task(agent_type="analysis", message="AI trends")
        result = await execute(task)
        mock_get.assert_called_once_with("analysis")
        assert "Analyzed: AI trends" == result["result"]

    @pytest.mark.asyncio
    @patch("services.workers.execution.task_runner.get_agent")
    async def test_unknown_type_falls_back(self, mock_get) -> None:
        mock_get.return_value = AsyncMock(return_value="Fallback: compare prices")
        task = _make_task(agent_type="unknown", message="compare prices")
        result = await execute(task)
        mock_get.assert_called_once_with("unknown")
        assert "result" in result

    @pytest.mark.asyncio
    @patch("services.workers.execution.task_runner.get_agent")
    async def test_result_includes_task_id(self, mock_get) -> None:
        mock_get.return_value = AsyncMock(return_value="done")
        task = _make_task()
        result = await execute(task)
        assert result["task_id"] == "t1"
