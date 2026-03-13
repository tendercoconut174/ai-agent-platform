"""Code agent – code execution, data processing, calculations."""

from services.agents.base_agent import create_react_agent

SYSTEM_PROMPT = (
    "You are a code execution agent. Your job is to write and run Python code "
    "for calculations, data processing, and analysis.\n\n"
    "Guidelines:\n"
    "- Use execute_python to run code. Available modules: math, json, re, datetime, "
    "collections, itertools, functools, statistics, csv, io.\n"
    "- Use read_file and write_file for file operations.\n"
    "- Always print results so they appear in stdout.\n"
    "- Handle errors gracefully.\n"
    "- For complex calculations, break them into steps."
)

_agent = create_react_agent("code", SYSTEM_PROMPT)


async def run(message: str) -> str:
    return await _agent(message)
