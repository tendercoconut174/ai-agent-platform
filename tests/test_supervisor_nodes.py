"""Unit tests for supervisor nodes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.orchestrator.supervisor.state import WorkflowState


class TestClassifyNode:
    """Tests for classify node."""

    @pytest.mark.asyncio
    @patch("shared.llm.is_llm_available")
    async def test_defaults_to_casual_when_no_llm(self, mock_available) -> None:
        """When LLM not available, defaults to casual."""
        mock_available.return_value = False
        from services.orchestrator.supervisor.nodes.classify import classify

        state: WorkflowState = {"goal": "hello", "conversation_history": []}
        result = await classify(state)
        assert result["intent"] == "casual"

    @pytest.mark.asyncio
    @patch("services.orchestrator.supervisor.nodes.classify._classify_with_llm", new_callable=AsyncMock)
    @patch("shared.llm.is_llm_available")
    async def test_returns_llm_intent(self, mock_available, mock_classify: AsyncMock) -> None:
        """When LLM available, returns classified intent."""
        mock_available.return_value = True
        mock_classify.return_value = ("complex", "Multi-step task")
        from services.orchestrator.supervisor.nodes.classify import classify

        state: WorkflowState = {"goal": "fetch news and email me", "conversation_history": []}
        result = await classify(state)
        assert result["intent"] == "complex"

    @pytest.mark.asyncio
    @patch("services.orchestrator.supervisor.nodes.classify._classify_with_llm", new_callable=AsyncMock)
    @patch("shared.llm.is_llm_available")
    async def test_returns_needs_clarification_intent(self, mock_available, mock_classify: AsyncMock) -> None:
        """When LLM detects vague request, returns needs_clarification intent."""
        mock_available.return_value = True
        mock_classify.return_value = ("needs_clarification", "Request too vague")
        from services.orchestrator.supervisor.nodes.classify import classify

        state: WorkflowState = {"goal": "research companies", "conversation_history": []}
        result = await classify(state)
        assert result["intent"] == "needs_clarification"

    @pytest.mark.asyncio
    async def test_shortcuts_to_complex_when_has_clarification(self) -> None:
        """When goal contains [User clarification], route to complex without calling LLM."""
        from services.orchestrator.supervisor.nodes.classify import classify

        state: WorkflowState = {
            "goal": "research companies\n\n[User clarification] petroleum sector",
            "conversation_history": [],
        }
        result = await classify(state)
        assert result["intent"] == "complex"


class TestAskUserNode:
    """Tests for ask_user node (human-in-the-loop)."""

    @pytest.mark.asyncio
    @patch("shared.llm.is_llm_available")
    async def test_returns_fallback_when_no_llm(self, mock_available) -> None:
        """When LLM not available, returns fallback question."""
        mock_available.return_value = False
        from services.orchestrator.supervisor.nodes.ask_user import ask_user

        state: WorkflowState = {"goal": "research companies"}
        result = await ask_user(state)
        assert result["needs_clarification"] is True
        assert result["clarification_question"] is not None
        assert len(result["clarification_question"]) > 0
        assert "detail" in result["clarification_question"].lower() or "more" in result["clarification_question"].lower()

    @pytest.mark.asyncio
    @patch("shared.llm.get_llm")
    @patch("shared.llm.is_llm_available")
    async def test_returns_llm_question_when_available(
        self, mock_available, mock_get_llm
    ) -> None:
        """When LLM available, returns generated clarifying question."""
        mock_available.return_value = True
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_result = MagicMock()
        mock_result.question = "Which industry are you interested in?"
        mock_result.reasoning = "Industry not specified"
        mock_structured.ainvoke = AsyncMock(return_value=mock_result)
        mock_llm.with_structured_output.return_value = mock_structured
        mock_get_llm.return_value = mock_llm

        from services.orchestrator.supervisor.nodes.ask_user import ask_user

        state: WorkflowState = {"goal": "research companies"}
        result = await ask_user(state)
        assert result["needs_clarification"] is True
        assert result["clarification_question"] == "Which industry are you interested in?"
        assert result["final_result"] == "Which industry are you interested in?"


class TestDeliverNode:
    """Tests for deliver node."""

    @pytest.mark.asyncio
    async def test_passes_through_final_result(self) -> None:
        """Deliver passes through final_result from state."""
        from services.orchestrator.supervisor.nodes.deliver import deliver

        state: WorkflowState = {
            "goal": "test",
            "final_result": "Here is the result",
            "output_format": "json",
        }
        result = await deliver(state)
        assert result["final_result"] == "Here is the result"

    @pytest.mark.asyncio
    async def test_uses_error_when_no_result(self) -> None:
        """When error and no result, uses error message."""
        from services.orchestrator.supervisor.nodes.deliver import deliver

        state: WorkflowState = {"goal": "test", "final_result": "", "error": "Something failed"}
        result = await deliver(state)
        assert "error" in result["final_result"].lower() or "Something failed" in result["final_result"]

    @pytest.mark.asyncio
    async def test_fallback_when_empty(self) -> None:
        """When no result and no error, returns fallback message."""
        from services.orchestrator.supervisor.nodes.deliver import deliver

        state: WorkflowState = {"goal": "test", "final_result": ""}
        result = await deliver(state)
        assert len(result["final_result"]) > 0
        assert "rephrase" in result["final_result"].lower() or "wasn't" in result["final_result"].lower()


class TestPlanNode:
    """Tests for plan node."""

    @pytest.mark.asyncio
    @patch("shared.llm.is_llm_available")
    async def test_default_plan_when_no_llm(self, mock_available) -> None:
        """When LLM not available, returns single research step."""
        mock_available.return_value = False
        from services.orchestrator.supervisor.nodes.plan import plan

        state: WorkflowState = {"goal": "search for X", "output_format": "json"}
        result = await plan(state)
        assert result["plan"] is not None
        assert len(result["plan"].steps) == 1
        assert result["plan"].steps[0].agent_type == "research"


class TestEvaluateNode:
    """Tests for evaluate node."""

    @pytest.mark.asyncio
    async def test_auto_accepts_simple_intent(self) -> None:
        """Simple intent auto-accepts without LLM."""
        from services.orchestrator.supervisor.nodes.evaluate import evaluate

        state: WorkflowState = {
            "goal": "test",
            "intent": "simple",
            "final_result": "Answer here",
            "iteration_count": 0,
            "max_iterations": 5,
        }
        result = await evaluate(state)
        assert result["goal_achieved"] is True

    @pytest.mark.asyncio
    async def test_max_iterations_accepts(self) -> None:
        """At max iterations, accepts regardless."""
        from services.orchestrator.supervisor.nodes.evaluate import evaluate

        state: WorkflowState = {
            "goal": "test",
            "intent": "complex",
            "final_result": "Partial",
            "iteration_count": 4,
            "max_iterations": 5,
        }
        result = await evaluate(state)
        assert result["goal_achieved"] is True
        assert result["iteration_count"] == 5
