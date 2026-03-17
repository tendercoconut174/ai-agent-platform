"""Code agent – code execution, data processing, calculations."""

import logging
import time

from services.agents.base_agent import create_react_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a code execution agent. You CAN and MUST run Python code using the execute_python tool. "
    "Never say you cannot run code – you have execute_python and it works.\n\n"
    "Guidelines:\n"
    "- ALWAYS use execute_python to run code when the user asks for execution, conversion, or implementation. "
    "Do not suggest the user run it themselves – run it for them.\n"
    "- Available modules: math, json, re, datetime, collections, itertools, functools, statistics, csv, io.\n"
    "- Use read_file and write_file for file operations.\n"
    "- Always print results so they appear in stdout.\n"
    "- Handle errors gracefully.\n"
    "- For complex calculations, break them into steps.\n\n"
    "Decision-making based on output:\n"
    "- Run code, inspect the output, then decide what to do next.\n"
    "- If the output shows an error, fix the code and run again.\n"
    "- If the output suggests a condition (e.g. value < threshold), run follow-up code to decide or branch.\n"
    "- You can call execute_python multiple times – use each run's output to inform your next step."
)

_agent = create_react_agent("code", SYSTEM_PROMPT)


async def run(message: str) -> str:
    t0 = time.perf_counter()
    logger.info("[code] START | msg_len=%d", len(message))
    try:
        result = await _agent(message)
        logger.info("[code] DONE | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
        return result
    except Exception as e:
        logger.exception("[code] FAILED | %.2fs: %s", time.perf_counter() - t0, e)
        raise
