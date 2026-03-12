"""MCP-style web search tool. Performs real web search via ddgs (metasearch)."""

from typing import List

from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    """Input for web search tool."""

    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=20, description="Maximum number of results")


class WebSearchResult(BaseModel):
    """Single search result."""

    title: str = Field(..., description="Result title")
    body: str = Field(..., description="Result snippet/body")
    href: str = Field(..., description="Result URL")


class WebSearchOutput(BaseModel):
    """Output from web search tool."""

    results: List[WebSearchResult] = Field(default_factory=list, description="Search results")
    count: int = Field(..., description="Number of results")


def web_search(query: str, max_results: int = 10) -> WebSearchOutput:
    """Perform web search and return structured results.

    Args:
        query: Search query.
        max_results: Maximum number of results (1-20).

    Returns:
        WebSearchOutput with results.
    """
    from ddgs import DDGS

    max_results = min(max(max_results, 1), 20)
    ddgs = DDGS()
    # Use bing backend for better e-commerce/product search results
    raw = list(ddgs.text(query, max_results=max_results, backend="bing"))
    results = [
        WebSearchResult(
            title=r.get("title", ""),
            body=r.get("body", ""),
            href=r.get("href", ""),
        )
        for r in raw
    ]
    return WebSearchOutput(results=results, count=len(results))
