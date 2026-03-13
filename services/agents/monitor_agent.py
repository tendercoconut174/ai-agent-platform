"""Monitor agent – long-running observation and tracking tasks."""

from services.agents.base_agent import create_react_agent

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
    return await _agent(message)
