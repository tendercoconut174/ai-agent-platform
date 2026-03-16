"""Unit tests for email sender tool."""

import os
from unittest.mock import MagicMock, patch

import pytest

from shared.mcp.tools.email_sender import send_email


class TestSendEmail:
    """Tests for send_email function."""

    def test_not_configured_returns_error(self) -> None:
        """When SMTP is not configured, returns error dict."""
        with patch.dict(os.environ, {"SMTP_HOST": "", "SMTP_USER": "", "SMTP_PASSWORD": ""}, clear=False):
            result = send_email("a@b.com", "Subject", "Body")
        assert result["success"] is False
        assert "SMTP_NOT_CONFIGURED" in result.get("error", "")
        assert "not configured" in result.get("message", "").lower()

    @patch("shared.mcp.tools.email_sender.smtplib.SMTP")
    def test_success_when_configured(self, mock_smtp_class: MagicMock) -> None:
        """When configured, sends email and returns success."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(
            os.environ,
            {"SMTP_HOST": "smtp.test.com", "SMTP_USER": "u", "SMTP_PASSWORD": "p"},
            clear=False,
        ):
            result = send_email("to@example.com", "Test", "Hello")

        assert result["success"] is True
        assert "to@example.com" in result["message"]
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("u", "p")
        mock_server.sendmail.assert_called_once()

    @patch("shared.mcp.tools.email_sender.smtplib.SMTP")
    def test_auth_failure_returns_error(self, mock_smtp_class: MagicMock) -> None:
        """SMTP auth failure returns error dict."""
        import smtplib

        mock_server = MagicMock()
        mock_server.starttls = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Bad credentials")
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict(
            os.environ,
            {"SMTP_HOST": "smtp.test.com", "SMTP_USER": "u", "SMTP_PASSWORD": "p"},
            clear=False,
        ):
            result = send_email("to@example.com", "Test", "Body")

        assert result["success"] is False
        assert "authentication" in result.get("message", "").lower() or "App Password" in result.get("message", "")
