"""MCP Client – agents use this to discover and invoke tools."""

import logging
from typing import Any

from shared.mcp.server import get_all_tools, get_tools_for_agent, list_tool_names

logger = logging.getLogger(__name__)


class MCPClient:
    """Client interface for agents to interact with the MCP tool server."""

    def __init__(self, agent_type: str = "general"):
        self.agent_type = agent_type
        self._tools = get_tools_for_agent(agent_type)

    @property
    def tools(self) -> list:
        """LangChain tools available to this agent."""
        return self._tools

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self._tools]

    def discover(self) -> list[dict[str, str]]:
        """List available tools with their descriptions."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools
        ]

    def invoke(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a tool by name."""
        for t in self._tools:
            if t.name == tool_name:
                return t.invoke(kwargs)
        raise ValueError(f"Tool '{tool_name}' not available for agent type '{self.agent_type}'")
