"""Base agent factory – creates async ReAct agents with MCP tools."""

import logging
import warnings
from collections.abc import Awaitable, Callable

warnings.filterwarnings("ignore", message=".*Pydantic V1.*Python 3.14.*", category=UserWarning)

from shared.llm import get_llm, is_llm_available
from shared.mcp.server import get_tools_for_agent

logger = logging.getLogger(__name__)


def create_react_agent(agent_type: str, system_prompt: str) -> Callable[[str], Awaitable[str]]:
    """Create an async ReAct agent with MCP tools.

    Args:
        agent_type: Type of agent (determines tool access).
        system_prompt: System prompt defining agent behavior.

    Returns:
        An async callable that takes a message and returns a result string.
    """
    tools = get_tools_for_agent(agent_type)

    async def run(message: str) -> str:
        if not is_llm_available("agents"):
            return f"[{agent_type}] No LLM API key configured. Message: {message}"

        from langchain.agents import create_agent

        llm = get_llm("agents", temperature=0)
        agent = create_agent(llm, tools, system_prompt=system_prompt)
        result = await agent.ainvoke({"messages": [{"role": "user", "content": message}]})

        messages = result.get("messages", [])
        tool_calls = sum(1 for m in messages if getattr(m, "type", "") == "tool")
        logger.info("[agent:%s] finished | %d messages | %d tool calls", agent_type, len(messages), tool_calls)

        if tool_calls == 0 and tools:
            logger.warning("[agent:%s] 0 tool calls with %d tools available – retrying with forced instruction", agent_type, len(tools))
            tool_names = ", ".join(t.name for t in tools)
            retry_msg = (
                f"You have these tools available: {tool_names}. "
                f"You MUST call at least one tool before answering. "
                f"Do NOT answer from memory.\n\nRequest: {message}"
            )
            result = await agent.ainvoke({"messages": [{"role": "user", "content": retry_msg}]})
            messages = result.get("messages", [])
            retry_tool_calls = sum(1 for m in messages if getattr(m, "type", "") == "tool")
            logger.info("[agent:%s] retry finished | %d messages | %d tool calls", agent_type, len(messages), retry_tool_calls)

        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and getattr(msg, "type", "") == "ai":
                return msg.content
        return f"[{agent_type}] Completed with no output."

    return run
