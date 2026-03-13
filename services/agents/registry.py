"""Agent registry – maps agent_type to async agent runner."""

from collections.abc import Awaitable, Callable

from services.agents import (
    analysis_agent,
    chat_agent,
    code_agent,
    generator_agent,
    monitor_agent,
    research_agent,
)

AgentRunner = Callable[[str], Awaitable[str]]

AGENT_REGISTRY: dict[str, AgentRunner] = {
    "research": research_agent.run,
    "analysis": analysis_agent.run,
    "generator": generator_agent.run,
    "code": code_agent.run,
    "monitor": monitor_agent.run,
    "chat": chat_agent.run,
}


def get_agent(agent_type: str) -> AgentRunner:
    """Get async agent runner by type. Falls back to research agent."""
    return AGENT_REGISTRY.get(agent_type, research_agent.run)


def list_agents() -> list[str]:
    """Return all registered agent types."""
    return list(AGENT_REGISTRY.keys())
