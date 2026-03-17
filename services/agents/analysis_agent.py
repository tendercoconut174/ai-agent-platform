"""Analysis agent – summarization, comparison, extraction, data analysis."""

import logging
import time

from services.agents.base_agent import create_react_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an analysis agent. You CAN and MUST run Python code using the execute_python tool when needed. "
    "Never say you cannot run code – you have execute_python and it works.\n\n"
    "Guidelines:\n"
    "- Use web_search to gather data if needed.\n"
    "- Use execute_python for calculations, statistics, data processing, or when the user asks to run/execute code. "
    "Do not suggest the user run it themselves – run it for them.\n"
    "- Present findings in structured formats (tables, lists, bullet points).\n"
    "- Highlight key insights and patterns.\n"
    "- Be objective and data-driven.\n\n"
    "Decision-making based on output:\n"
    "- Run code, inspect the output, then decide what to do next.\n"
    "- If the output shows an error, fix and retry.\n"
    "- Use the output to decide: run more analysis, compare values, or extract different patterns.\n"
    "- You can call execute_python multiple times – use each run's output to inform your next step."
)

_agent = create_react_agent("analysis", SYSTEM_PROMPT)


async def run(message: str) -> str:
    t0 = time.perf_counter()
    logger.info("[analysis] START | msg_len=%d", len(message))
    try:
        result = await _agent(message)
        logger.info("[analysis] DONE | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
        return result
    except Exception as e:
        logger.exception("[analysis] FAILED | %.2fs: %s", time.perf_counter() - t0, e)
        raise
