"""Unit tests for chat, generator, code, analysis, monitor agents."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestChatAgent:
    """Tests for chat agent."""

    @pytest.mark.asyncio
    @patch("services.agents.chat_agent.is_llm_available")
    async def test_no_llm_returns_fallback(self, mock_available) -> None:
        """When LLM not available, returns fallback message."""
        mock_available.return_value = False
        from services.agents import chat_agent

        result = await chat_agent.run("hello")
        assert "No LLM" in result or "assistant" in result

    @pytest.mark.asyncio
    @patch("services.agents.chat_agent.get_llm")
    @patch("services.agents.chat_agent.is_llm_available")
    async def test_with_llm_returns_string(self, mock_available, mock_get_llm) -> None:
        """With LLM, returns non-empty string."""
        mock_available.return_value = True
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Hi there!"))
        mock_get_llm.return_value = mock_llm
        from services.agents import chat_agent

        result = await chat_agent.run("hello")
        assert result == "Hi there!"


class TestGeneratorAgent:
    """Tests for generator agent."""

    @pytest.mark.asyncio
    @patch("services.agents.base_agent.create_react_agent")
    async def test_returns_string(self, mock_factory) -> None:
        """Generator agent returns string."""
        mock_agent = AsyncMock(return_value="Generated report")
        mock_factory.return_value = mock_agent
        from services.agents import generator_agent

        result = await generator_agent.run("create a report")
        assert isinstance(result, str)
        assert "Generated" in result or "report" in result


class TestCodeAgent:
    """Tests for code agent."""

    @pytest.mark.asyncio
    @patch("services.agents.base_agent.create_react_agent")
    async def test_returns_string(self, mock_factory) -> None:
        """Code agent returns string."""
        mock_agent = AsyncMock(return_value="Code output: 42")
        mock_factory.return_value = mock_agent
        from services.agents import code_agent

        result = await code_agent.run("print(42)")
        assert isinstance(result, str)


class TestAnalysisAgent:
    """Tests for analysis agent."""

    @pytest.mark.asyncio
    @patch("services.agents.base_agent.create_react_agent")
    async def test_returns_string(self, mock_factory) -> None:
        """Analysis agent returns string."""
        mock_agent = AsyncMock(return_value="Analysis summary")
        mock_factory.return_value = mock_agent
        from services.agents import analysis_agent

        result = await analysis_agent.run("summarize this")
        assert isinstance(result, str)


class TestMonitorAgent:
    """Tests for monitor agent."""

    @pytest.mark.asyncio
    @patch("services.agents.base_agent.create_react_agent")
    async def test_returns_string(self, mock_factory) -> None:
        """Monitor agent returns string."""
        mock_agent = AsyncMock(return_value="Monitoring result")
        mock_factory.return_value = mock_agent
        from services.agents import monitor_agent

        result = await monitor_agent.run("track news")
        assert isinstance(result, str)
