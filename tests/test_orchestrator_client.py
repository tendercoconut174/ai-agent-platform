"""Unit tests for orchestrator client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.gateway.api.orchestrator_client import call_orchestrator


class TestCallOrchestrator:
    """Tests for call_orchestrator."""

    @pytest.mark.asyncio
    @patch("services.gateway.api.orchestrator_client.httpx.AsyncClient")
    async def test_sends_correct_payload(self, mock_client_class: MagicMock) -> None:
        """call_orchestrator sends message and options in JSON body."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await call_orchestrator(
            message="hello",
            output_format="json",
            session_id="s1",
            conversation_history=[{"role": "user", "content": "hi"}],
        )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["message"] == "hello"
        assert call_kwargs["json"]["session_id"] == "s1"
        assert call_kwargs["json"]["conversation_history"] == [{"role": "user", "content": "hi"}]
        assert call_kwargs["json"]["require_code_approval"] is False
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    @patch("services.gateway.api.orchestrator_client.httpx.AsyncClient")
    async def test_sends_require_code_approval_when_true(self, mock_client_class: MagicMock) -> None:
        """call_orchestrator includes require_code_approval in payload when True."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await call_orchestrator(
            message="calculate 2+2",
            require_code_approval=True,
        )

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["require_code_approval"] is True
