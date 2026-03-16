"""Integration tests for API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.gateway.main import app


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
