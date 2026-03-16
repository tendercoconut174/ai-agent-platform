"""Unit tests for URL scraper tool."""

from unittest.mock import MagicMock, patch

import pytest

from shared.mcp.tools.url_scraper import scrape_url


class TestScrapeUrl:
    """Tests for scrape_url function."""

    @patch("shared.mcp.tools.url_scraper.httpx.get")
    def test_returns_title_and_text(self, mock_get: MagicMock) -> None:
        """Successful scrape returns title and text."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head><title>Test Page</title></head><body><p>Hello world</p></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = scrape_url("https://example.com/page")

        assert result["url"] == "https://example.com/page"
        assert "Test Page" in result.get("title", "")
        assert "Hello" in result.get("text", "") or "world" in result.get("text", "")
        assert result.get("status_code") == 200
        assert "error" not in result or not result["error"]

    @patch("shared.mcp.tools.url_scraper.httpx.get")
    def test_respects_max_length(self, mock_get: MagicMock) -> None:
        """Text is truncated to max_length."""
        long_body = "x" * 10000
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = f"<html><head><title>T</title></head><body><p>{long_body}</p></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = scrape_url("https://example.com", max_length=100)

        assert len(result.get("text", "")) <= 100

    @patch("shared.mcp.tools.url_scraper.httpx.get")
    def test_http_error_returns_error_dict(self, mock_get: MagicMock) -> None:
        """HTTP errors return error in result."""
        import httpx

        mock_get.side_effect = httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())

        result = scrape_url("https://example.com/404")

        assert "error" in result
        assert result.get("status_code", 0) == 0 or "error" in result
