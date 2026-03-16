"""Tests for orchestrator API routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.orchestrator.main import app


@pytest.fixture
def orchestrator_client() -> TestClient:
    """Orchestrator FastAPI test client."""
    return TestClient(app)


class TestOrchestrateEndpoint:
    """Tests for POST /orchestrate."""

    @patch("services.orchestrator.api.routes.run_workflow", new_callable=AsyncMock)
    def test_returns_needs_clarification_when_workflow_asks(
        self, mock_run: AsyncMock, orchestrator_client: TestClient
    ) -> None:
        """When workflow returns needs_clarification, orchestrator returns it without deliver."""
        mock_run.return_value = {
            "workflow_id": "wf-123",
            "needs_clarification": True,
            "clarification_question": "Which industry?",
            "final_result": "Which industry?",
        }
        response = orchestrator_client.post(
            "/orchestrate",
            json={
                "message": "research companies",
                "output_format": "json",
                "conversation_history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_clarification"] is True
        assert data["question"] == "Which industry?"
        assert data["workflow_id"] == "wf-123"
