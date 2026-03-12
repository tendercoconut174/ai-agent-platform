"""Unit tests for research agent."""

import pytest

from services.workers.agents.research_agent import run_research_agent


class TestRunResearchAgent:
    """Tests for run_research_agent."""

    def test_returns_structured_result(self) -> None:
        """Return TaskResult with result field."""
        result = run_research_agent("climate change")
        assert result.result == "Research result for climate change"

    def test_result_includes_query(self) -> None:
        """Result includes the query in output."""
        result = run_research_agent("AI trends")
        assert "AI trends" in result.result
