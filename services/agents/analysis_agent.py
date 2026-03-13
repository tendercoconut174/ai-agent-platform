"""Analysis agent – summarization, comparison, extraction, data analysis."""

from services.agents.base_agent import create_react_agent

SYSTEM_PROMPT = (
    "You are an analysis agent. Your job is to analyze data, summarize information, "
    "compare items, and extract patterns.\n\n"
    "Guidelines:\n"
    "- Use web_search to gather data if needed.\n"
    "- Use execute_python for calculations, statistics, or data processing.\n"
    "- Present findings in structured formats (tables, lists, bullet points).\n"
    "- Highlight key insights and patterns.\n"
    "- Be objective and data-driven."
)

_agent = create_react_agent("analysis", SYSTEM_PROMPT)


async def run(message: str) -> str:
    return await _agent(message)
