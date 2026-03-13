"""Unit tests for web search tool."""

from shared.mcp.tools.web_search import web_search


class TestWebSearch:
    """Tests for web_search tool."""

    def test_returns_structured_output(self) -> None:
        """Return list of dicts with title, body, href."""
        results = web_search("Python programming", max_results=3)
        assert isinstance(results, list)
        assert len(results) <= 3
        for r in results:
            assert "title" in r
            assert "body" in r
            assert "href" in r

    def test_respects_max_results(self) -> None:
        """Respect max_results limit."""
        results = web_search("test query", max_results=2)
        assert len(results) <= 2
