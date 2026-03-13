"""Unit tests for shared models."""

import pytest
from pydantic import ValidationError

from shared.models import (
    AgentMessage,
    MessageRequest,
    MessageResponse,
    OrchestratorRequest,
    TaskPayload,
    TaskResult,
    WorkflowResponse,
)


class TestMessageRequest:
    """Tests for MessageRequest model."""

    def test_valid_message(self) -> None:
        req = MessageRequest(message="research climate change")
        assert req.message == "research climate change"
        assert req.output_format == "json"
        assert req.mode == "auto"

    def test_message_required(self) -> None:
        with pytest.raises(ValidationError):
            MessageRequest()

    def test_optional_fields(self) -> None:
        req = MessageRequest(
            message="hello",
            output_format="pdf",
            mode="chat",
            session_id="sess-1",
        )
        assert req.output_format == "pdf"
        assert req.mode == "chat"
        assert req.session_id == "sess-1"


class TestTaskPayload:
    """Tests for TaskPayload model."""

    def test_valid_payload(self) -> None:
        payload = TaskPayload(
            task_id="abc-123",
            workflow_id="wf-1",
            step_id="step-1",
            agent_type="research",
            message="research AI",
        )
        assert payload.task_id == "abc-123"
        assert payload.agent_type == "research"

    def test_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            TaskPayload(task_id="abc-123", message="research AI")


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_valid_result(self) -> None:
        result = TaskResult(result="Research result for query")
        assert result.result == "Research result for query"
        assert result.error is None

    def test_with_error(self) -> None:
        result = TaskResult(result="", error="timeout")
        assert result.error == "timeout"


class TestAgentMessage:
    """Tests for AgentMessage model."""

    def test_valid_message(self) -> None:
        msg = AgentMessage(
            from_agent="research",
            message_type="result",
            content="done",
        )
        assert msg.from_agent == "research"
        assert msg.to_agent == "supervisor"

    def test_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            AgentMessage(from_agent="research")


class TestMessageResponse:
    """Tests for MessageResponse model."""

    def test_defaults(self) -> None:
        resp = MessageResponse(result="hello")
        assert resp.output_format == "json"
        assert resp.content_base64 is None


class TestOrchestratorRequest:
    """Tests for OrchestratorRequest model."""

    def test_defaults(self) -> None:
        req = OrchestratorRequest(message="do something")
        assert req.mode == "auto"
        assert req.output_format == "json"


class TestWorkflowResponse:
    """Tests for WorkflowResponse model."""

    def test_valid(self) -> None:
        resp = WorkflowResponse(workflow_id="wf-1", status="pending")
        assert resp.message == "Workflow created"
