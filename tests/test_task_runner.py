"""Unit tests for task runner."""

import pytest

from services.workers.execution.task_runner import execute
from shared.models import TaskPayload


class TestExecute:
    """Tests for execute function."""

    def test_research_task_routes_to_agent(self) -> None:
        """Route research task_type to research agent."""
        task = TaskPayload(task_id="t1", message="research AI", task_type="research")
        result = execute(task)
        assert "research AI" in result["result"]

    def test_task_type_routes_to_agent(self) -> None:
        """Route by task_type to specialized agent."""
        task = TaskPayload(task_id="t2", message="AI trends", task_type="research")
        result = execute(task)
        assert "AI trends" in result["result"]

    def test_general_task_routes_to_general_agent(self) -> None:
        """Route general or unknown task_type to general agent."""
        task = TaskPayload(task_id="t3", message="compare prices", task_type="general")
        result = execute(task)
        assert "result" in result
        assert "compare prices" in result["result"] or "General task" in result["result"]
