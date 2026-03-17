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


class TestPlanExecuteAgent:
    """Tests for plan_execute agent."""

    @pytest.mark.asyncio
    @patch("services.agents.plan_execute_agent.is_llm_available")
    async def test_no_llm_returns_fallback(self, mock_available) -> None:
        """When LLM not available, returns fallback message."""
        mock_available.return_value = False
        from services.agents import plan_execute_agent

        result = await plan_execute_agent.run("complex task")
        assert "No LLM" in result or "different agent" in result

    @pytest.mark.asyncio
    @patch("services.agents.plan_execute_agent._executor", new_callable=AsyncMock)
    @patch("services.agents.plan_execute_agent.get_llm")
    @patch("services.agents.plan_execute_agent.is_llm_available")
    async def test_returns_executor_result(
        self, mock_available, mock_get_llm, mock_executor: AsyncMock
    ) -> None:
        """With LLM, plans and returns executor result."""
        mock_available.return_value = True
        mock_structured = MagicMock()
        mock_plan = MagicMock()
        mock_plan.steps = [
            MagicMock(step_id="step_1", instruction="Do X", tool_hint="web_search"),
        ]
        mock_plan.reasoning = "Single step"
        mock_structured.ainvoke = AsyncMock(return_value=mock_plan)
        mock_get_llm.return_value.with_structured_output.return_value = mock_structured
        mock_executor.return_value = "Executor output for step 1"

        from services.agents import plan_execute_agent

        result = await plan_execute_agent.run("research X")
        assert "Executor output" in result or "step 1" in result or "step_1" in result


class TestAgentRegistry:
    """Tests for agent registry."""

    def test_list_agents_includes_all_types(self) -> None:
        """list_agents returns all registered agent types including scheduler."""
        from services.agents.registry import list_agents

        agents = list_agents()
        assert "research" in agents
        assert "scheduler" in agents
        assert "plan_execute" in agents
        assert "code" in agents

    def test_get_agent_scheduler_returns_scheduler_run(self) -> None:
        """get_agent('scheduler') returns scheduler agent run function."""
        from services.agents.registry import get_agent

        runner = get_agent("scheduler")
        assert runner is not None
        assert callable(runner)
