"""Research agent – web search, data gathering, fact-finding.

Uses a two-phase approach to guarantee web search:
  1. Always executes web_search directly (no LLM decision)
  2. If pre-search succeeds: synthesize with LLM (fast, no tools needed)
  3. If pre-search fails: fall back to full ReAct agent with tools
"""

import logging
import time

from services.agents.base_agent import create_react_agent
from shared.llm import get_llm, is_llm_available

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a research agent. Your job is to find accurate, up-to-date information from the web.\n\n"
    "You MUST use tool_web_search for EVERY request -- no exceptions. "
    "Even if you think you know the answer, search first.\n\n"
    "Guidelines:\n"
    "- Call tool_web_search with a well-crafted query as your first action\n"
    "- Use tool_scrape_url to get details from specific URLs when needed\n"
    "- Cite sources with URLs\n"
    "- If asked for tabular data, format as markdown tables\n"
    "- Provide concise, well-structured summaries"
)

_SYNTH_SYSTEM = (
    "You are a research synthesizer. You have been given web search results. "
    "Synthesize them into a clear, accurate answer. "
    "Cite sources with URLs. Use markdown tables for tabular data. "
    "Never fabricate information not present in the search results."
)

_agent = create_react_agent("research", SYSTEM_PROMPT)


async def _pre_search(query: str) -> str:
    """Always-execute web search -- bypasses LLM tool-call decision."""
    from shared.mcp.server import tool_web_search

    try:
        return tool_web_search.invoke({"query": query})
    except Exception as exc:
        logger.warning("[research] pre-search failed: %s", exc)
        return ""


async def run(message: str) -> str:
    t0 = time.perf_counter()
    logger.info("[research] START | msg_len=%d", len(message))

    if not is_llm_available("agents"):
        logger.warning("[research] No LLM configured")
        return f"[research] No LLM API key configured. Message: {message}"

    search_results = await _pre_search(message)

    if search_results and search_results != "No results found.":
        logger.info("[research] pre-search returned %d chars, synthesizing directly", len(search_results))
        llm = get_llm("agents", temperature=0)
        response = await llm.ainvoke([
            {"role": "system", "content": _SYNTH_SYSTEM},
            {"role": "user", "content": (
                f"=== WEB SEARCH RESULTS ===\n{search_results}\n=== END ===\n\n"
                f"Answer this question using the search results above: {message}"
            )},
        ])
        result = (response.content or "").strip()
        if result:
            logger.info("[research] DONE | synthesis | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
            return result

    logger.warning("[research] pre-search empty or synthesis failed, using full ReAct agent")
    result = await _agent(message)
    logger.info("[research] DONE | ReAct fallback | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
    return result
