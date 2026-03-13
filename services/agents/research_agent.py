"""Research agent – web search, data gathering, fact-finding.

Uses a two-phase approach to guarantee web search:
  1. Always executes web_search first (no LLM decision)
  2. Feeds results to a ReAct agent for synthesis and optional deeper research
"""

import logging

from services.agents.base_agent import create_react_agent
from shared.llm import get_llm, is_llm_available

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a research agent. You have been given web search results as context. "
    "Your job is to synthesize these results into a clear, accurate answer.\n\n"
    "Guidelines:\n"
    "- Use the provided search results as your primary source of truth\n"
    "- If the search results are insufficient, use tool_web_search with a refined query\n"
    "- Use tool_scrape_url to get more details from specific URLs in the results\n"
    "- Cite sources with URLs\n"
    "- If asked for tabular data, format as markdown tables\n"
    "- Provide concise, well-structured summaries\n"
    "- Never fabricate information not present in search results or tool output"
)

_agent = create_react_agent("research", SYSTEM_PROMPT)


async def _pre_search(query: str) -> str:
    """Always-execute web search – bypasses LLM tool-call decision."""
    from shared.mcp.server import tool_web_search

    try:
        return tool_web_search.invoke({"query": query})
    except Exception as exc:
        logger.warning("[research] pre-search failed: %s", exc)
        return ""


async def run(message: str) -> str:
    if not is_llm_available("agents"):
        return f"[research] No LLM API key configured. Message: {message}"

    search_results = await _pre_search(message)

    if search_results and search_results != "No results found.":
        logger.info("[research] pre-search returned %d chars", len(search_results))
        enhanced = (
            f"=== WEB SEARCH RESULTS ===\n{search_results}\n"
            f"=== END SEARCH RESULTS ===\n\n"
            f"Using the search results above, answer: {message}"
        )
        return await _agent(enhanced)

    logger.warning("[research] pre-search empty, falling back to full agent")
    return await _agent(message)
