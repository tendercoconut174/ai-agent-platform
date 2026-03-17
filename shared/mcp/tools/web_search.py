"""Web search tool via ddgs (DuckDuckGo metasearch)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BACKENDS = ["duckduckgo", "brave", "mojeek", "yahoo"]


def web_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search the web and return structured results.

    Tries the default (auto) backend first, then falls back to specific backends.

    Args:
        query: Search query string.
        max_results: Number of results (1-20).

    Returns:
        List of dicts with title, body, href.
    """
    logger.info("[web_search] web_search | query=%s | max_results=%d", query[:60], max_results)
    from ddgs import DDGS

    max_results = min(max(max_results, 1), 20)
    ddgs = DDGS()

    def _parse(raw: list) -> list[dict[str, Any]]:
        return [
            {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
            for r in raw
        ]

    try:
        raw = list(ddgs.text(query, max_results=max_results))
        if raw:
            parsed = _parse(raw)
            logger.info("[web_search] DONE | result_count=%d", len(parsed))
            return parsed
    except Exception as exc:
        logger.debug("[web_search] Default backend failed: %s", exc)

    for backend in _BACKENDS:
        try:
            raw = list(ddgs.text(query, max_results=max_results, backend=backend))
            if raw:
                logger.debug("[web_search] Succeeded with backend=%s", backend)
                return _parse(raw)
        except Exception as exc:
            logger.debug("[web_search] Backend %s failed: %s", backend, exc)
            continue

    logger.warning("[web_search] All backends failed for query=%s", query[:60])
    return []
