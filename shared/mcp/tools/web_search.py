"""Web search tool via ddgs (DuckDuckGo metasearch)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BACKENDS = ["google", "duckduckgo", "brave", "yahoo"]


def web_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search the web and return structured results.

    Tries multiple backends in order until one succeeds.

    Args:
        query: Search query string.
        max_results: Number of results (1-20).

    Returns:
        List of dicts with title, body, href.
    """
    from ddgs import DDGS

    max_results = min(max(max_results, 1), 20)
    ddgs = DDGS()

    for backend in _BACKENDS:
        try:
            raw = list(ddgs.text(query, max_results=max_results, backend=backend))
            if raw:
                return [
                    {
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "href": r.get("href", ""),
                    }
                    for r in raw
                ]
        except Exception as exc:
            logger.debug("Search backend %s failed: %s", backend, exc)
            continue

    return []
