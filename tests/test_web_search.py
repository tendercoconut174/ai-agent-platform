"""Unit tests for web search tool."""

import pytest

from shared.tools.web_search import web_search


class TestWebSearch:
    """Tests for web_search tool."""

    def test_returns_structured_output(self) -> None:
        """Return WebSearchOutput with results."""
        result = web_search("Python programming", max_results=3)
        assert result.count >= 0
        assert len(result.results) <= 3
        for r in result.results:
            assert hasattr(r, "title")
            assert hasattr(r, "body")
            assert hasattr(r, "href")

    def test_respects_max_results(self) -> None:
        """Respect max_results limit."""
        result = web_search("test query", max_results=2)
        assert len(result.results) <= 2
