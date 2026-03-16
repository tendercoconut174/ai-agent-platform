"""Integration tests for API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.gateway.main import app


class TestMessageStreamEndpoint:
    """Tests for /message/stream SSE endpoint."""

    @patch("services.gateway.api.routes.stream_orchestrator")
    def test_stream_returns_sse_events(
        self,
        mock_stream: AsyncMock,
        client: TestClient,
    ) -> None:
        """Stream endpoint returns SSE events from orchestrator."""
        async def gen():
            yield {"type": "step", "node_id": "execute"}
            yield {"type": "done", "delivery": {"result": "Done."}}

        mock_stream.return_value = gen()

        response = client.post(
            "/message/stream",
            json={"message": "hello"},
            headers={"Accept": "text/event-stream"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        assert "step" in body or "done" in body or "data:" in body

    @patch("services.gateway.api.routes.stream_orchestrator")
    def test_stream_passes_require_code_approval(
        self,
        mock_stream: AsyncMock,
        client: TestClient,
    ) -> None:
        """Stream endpoint passes require_code_approval to orchestrator."""
        async def gen():
            yield {"type": "done", "delivery": {"result": "ok"}}

        mock_stream.return_value = gen()

        client.post(
            "/message/stream",
            json={"message": "calculate", "require_code_approval": True},
            headers={"Accept": "text/event-stream"},
        )
        call_kwargs = mock_stream.call_args[1]
        assert call_kwargs.get("require_code_approval") is True


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Health endpoint returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMessageEndpoint:
    """Tests for /message endpoint."""

    @patch("services.gateway.api.routes.call_orchestrator", new_callable=AsyncMock)
    def test_message_returns_result_when_orchestrator_responds(
        self,
        mock_call: AsyncMock,
        client: TestClient,
    ) -> None:
        """Message endpoint returns result when orchestrator responds."""
        mock_call.return_value = {"result": "Research result for test"}
        response = client.post(
            "/message",
            json={"message": "research test"},
        )
        assert response.status_code == 200
        assert response.json()["result"] == "Research result for test"

    @patch("services.gateway.api.routes.call_orchestrator", new_callable=AsyncMock)
    def test_message_returns_timeout_when_orchestrator_times_out(
        self,
        mock_call: AsyncMock,
        client: TestClient,
    ) -> None:
        """Message endpoint returns timeout when orchestrator times out."""
        mock_call.return_value = {"status": "timeout", "result": "Request timed out"}
        response = client.post(
            "/message",
            json={"message": "research test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "timeout"

    @patch("services.gateway.api.routes.call_orchestrator", new_callable=AsyncMock)
    def test_message_returns_needs_clarification_when_orchestrator_asks(
        self,
        mock_call: AsyncMock,
        client: TestClient,
    ) -> None:
        """Message endpoint returns needs_clarification when orchestrator asks for clarification."""
        mock_call.return_value = {
            "result": "Which industry are you interested in?",
            "workflow_id": "wf-abc-123",
            "output_format": "json",
            "session_id": "sess-xyz",
            "needs_clarification": True,
            "question": "Which industry are you interested in?",
        }
        response = client.post(
            "/message",
            json={"message": "research companies"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_clarification"] is True
        assert data["question"] == "Which industry are you interested in?"
        assert data["workflow_id"] == "wf-abc-123"

    @patch("services.gateway.api.routes.call_orchestrator", new_callable=AsyncMock)
    def test_message_resume_with_workflow_id_merges_goal(
        self,
        mock_call: AsyncMock,
        client: TestClient,
    ) -> None:
        """When workflow_id provided and pending exists, gateway merges goal and resumes."""
        from unittest.mock import patch

        with patch(
            "services.gateway.api.routes.load_and_clear_pending_clarification",
        ) as mock_load:
            from services.gateway.pending_clarification_manager import (
                PendingClarificationRecord,
            )

            mock_load.return_value = PendingClarificationRecord(
                workflow_id="wf-resume",
                session_id="sess-1",
                original_goal="research companies",
                question="Which industry?",
                output_format="json",
            )
            mock_call.return_value = {"result": "Here are tech companies..."}

            response = client.post(
                "/message",
                json={
                    "message": "tech sector",
                    "workflow_id": "wf-resume",
                    "session_id": "sess-1",
                },
            )
            assert response.status_code == 200
            assert mock_load.called
            call_kwargs = mock_call.call_args[1]
            sent_message = call_kwargs.get("message", "")
            assert "research companies" in sent_message
            assert "[User clarification]" in sent_message
            assert "tech sector" in sent_message

    @patch("services.gateway.api.routes.call_orchestrator", new_callable=AsyncMock)
    def test_message_returns_needs_code_approval_when_orchestrator_asks(
        self,
        mock_call: AsyncMock,
        client: TestClient,
    ) -> None:
        """Message endpoint returns needs_code_approval when orchestrator asks for code approval."""
        mock_call.return_value = {
            "result": "I've prepared code. Please approve and run it.",
            "workflow_id": "wf-code-123",
            "output_format": "json",
            "session_id": "sess-xyz",
            "needs_code_approval": True,
            "code_approval_id": "approval-abc-456",
            "code": "print(2 + 2)",
        }
        response = client.post(
            "/message",
            json={"message": "calculate 2+2", "require_code_approval": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_code_approval"] is True
        assert data["code_approval_id"] == "approval-abc-456"
        assert data["code"] == "print(2 + 2)"
        call_kwargs = mock_call.call_args[1]
        assert call_kwargs.get("require_code_approval") is True

    @patch("services.gateway.api.routes.call_orchestrator", new_callable=AsyncMock)
    def test_message_resume_with_code_approval_id_runs_code_and_forwards(
        self,
        mock_call: AsyncMock,
        client: TestClient,
    ) -> None:
        """When code_approval_id provided and pending exists, gateway runs code and forwards output."""
        from shared.pending_code_approval_manager import PendingCodeApprovalRecord

        with patch(
            "services.gateway.api.routes.load_and_clear_pending_code_approval",
        ) as mock_load:
            with patch(
                "shared.mcp.tools.code_executor.execute_python",
            ) as mock_exec:
                mock_load.return_value = PendingCodeApprovalRecord(
                    approval_id="approval-123",
                    workflow_id="wf-1",
                    session_id="sess-1",
                    code="print(2 + 2)",
                    step_id="step-1",
                    original_goal="calculate 2+2",
                    output_format="json",
                )
                mock_exec.return_value = {"stdout": "4", "stderr": "", "error": None}
                mock_call.return_value = {"result": "The result is 4."}

                response = client.post(
                    "/message",
                    json={
                        "message": "approved",
                        "code_approval_id": "approval-123",
                        "session_id": "sess-1",
                    },
                )
                assert response.status_code == 200
                assert mock_load.called
                assert mock_exec.called
                mock_exec.assert_called_once_with("print(2 + 2)")
                call_kwargs = mock_call.call_args[1]
                sent_message = call_kwargs.get("message", "")
                assert "[Code approved and executed]" in sent_message
                assert "Output:" in sent_message
                assert "4" in sent_message
                assert "calculate 2+2" in sent_message
