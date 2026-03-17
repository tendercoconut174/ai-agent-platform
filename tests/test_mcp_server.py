"""Unit tests for MCP server tool registry."""

import pytest

from shared.mcp.server import get_tools_for_agent, get_all_tools, list_tool_names


class TestMcpServer:
    """Tests for MCP tool registry."""

    def test_research_has_web_search_and_scrape(self) -> None:
        """Research agent has web_search and scrape_url."""
        tools = get_tools_for_agent("research")
        names = [t.name for t in tools]
        assert "tool_web_search" in names
        assert "tool_scrape_url" in names

    def test_generator_has_send_email(self) -> None:
        """Generator agent has send_email tool."""
        tools = get_tools_for_agent("generator")
        names = [t.name for t in tools]
        assert "tool_send_email" in names

    def test_chat_has_no_tools(self) -> None:
        """Chat agent has no tools."""
        tools = get_tools_for_agent("chat")
        assert tools == []

    def test_code_has_execute_python(self) -> None:
        """Code agent has execute_python."""
        tools = get_tools_for_agent("code")
        names = [t.name for t in tools]
        assert "tool_execute_python" in names

    def test_unknown_agent_returns_empty(self) -> None:
        """Unknown agent type returns empty list."""
        tools = get_tools_for_agent("unknown_type")
        assert tools == []

    def test_scheduler_has_schedule_tools(self) -> None:
        """Scheduler agent has schedule, list, and cancel tools."""
        tools = get_tools_for_agent("scheduler")
        names = [t.name for t in tools]
        assert "tool_schedule_task" in names
        assert "tool_list_scheduled_tasks" in names
        assert "tool_cancel_scheduled_task" in names

    def test_get_all_tools_includes_send_email(self) -> None:
        """get_all_tools includes tool_send_email."""
        all_tools = get_all_tools()
        names = [t.name for t in all_tools]
        assert "tool_send_email" in names

    def test_get_all_tools_includes_scheduler_tools(self) -> None:
        """get_all_tools includes scheduler tools."""
        all_tools = get_all_tools()
        names = [t.name for t in all_tools]
        assert "tool_schedule_task" in names
        assert "tool_list_scheduled_tasks" in names
        assert "tool_cancel_scheduled_task" in names

    def test_list_tool_names_returns_strings(self) -> None:
        """list_tool_names returns list of tool name strings."""
        names = list_tool_names()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)
