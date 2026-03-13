"""Unit tests for research agent."""

from unittest.mock import AsyncMock, patch

import pytest

from services.agents.research_agent import run


class TestResearchAgent:
    """Tests for the research agent's async run function."""

    @pytest.mark.asyncio
    @patch("services.agents.base_agent.create_react_agent")
    async def test_returns_string_result(self, mock_factory) -> None:
        """Agent returns a string result."""
        mock_agent = AsyncMock(side_effect=lambda msg: f"Research result for {msg}")
        mock_factory.return_value = mock_agent

        from importlib import reload
        import services.agents.research_agent as mod
        reload(mod)

        result = await mod.run("climate change")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_is_callable(self) -> None:
        """run is a callable."""
        assert callable(run)
