"""Monitor agent – long-running observation and tracking tasks."""

import logging
import time

from services.agents.base_agent import create_react_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a monitoring agent. Your job is to observe, track, and report on "
    "ongoing events or data over time.\n\n"
    "Guidelines:\n"
    "- Use web_search to check current state of things.\n"
    "- Use scrape_url to monitor specific pages.\n"
    "- Summarize what you find clearly.\n"
    "- Note any changes or notable events.\n"
    "- Provide timestamps where relevant."
)

_agent = create_react_agent("monitor", SYSTEM_PROMPT)


async def run(message: str) -> str:
    t0 = time.perf_counter()
    logger.info("[monitor] START | msg_len=%d", len(message))
    try:
        result = await _agent(message)
        logger.info("[monitor] DONE | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
        return result
    except Exception as e:
        logger.exception("[monitor] FAILED | %.2fs: %s", time.perf_counter() - t0, e)
        raise
