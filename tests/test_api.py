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
