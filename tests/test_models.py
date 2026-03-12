"""Unit tests for shared models."""

import pytest
from pydantic import ValidationError

from shared.models import AgentState, MessageRequest, TaskPayload, TaskResult


class TestMessageRequest:
    """Tests for MessageRequest model."""

    def test_valid_message(self) -> None:
        """Accept valid message."""
        req = MessageRequest(message="research climate change")
        assert req.message == "research climate change"

    def test_message_required(self) -> None:
        """Reject missing message."""
        with pytest.raises(ValidationError):
            MessageRequest()


class TestTaskPayload:
    """Tests for TaskPayload model."""

    def test_valid_payload(self) -> None:
        """Accept valid task payload."""
        payload = TaskPayload(task_id="abc-123", message="research AI")
        assert payload.task_id == "abc-123"
        assert payload.message == "research AI"


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_valid_result(self) -> None:
        """Accept valid result."""
        result = TaskResult(result="Research result for query")
        assert result.result == "Research result for query"


class TestAgentState:
    """Tests for AgentState model."""

    def test_with_result(self) -> None:
        """State with result."""
        state = AgentState(task="query", result="answer")
        assert state.task == "query"
        assert state.result == "answer"

    def test_without_result(self) -> None:
        """State without result defaults to None."""
        state = AgentState(task="query")
        assert state.result is None
