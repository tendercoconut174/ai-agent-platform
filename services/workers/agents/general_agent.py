"""General agent: OpenAI agent with web search tool for real data."""

import os
import warnings

# Suppress LangChain Pydantic v1 + Python 3.14 warning
warnings.filterwarnings("ignore", message=".*Pydantic V1.*Python 3.14.*", category=UserWarning)

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from shared.models import TaskResult


def _create_web_search_tool():
    """Create LangChain tool for web search."""

    @tool
    def web_search(query: str, max_results: int = 10) -> str:
        """Search the web for real, current information. Use this for price comparisons,
        product info, news, or any data that needs to be fetched from the internet.
        Returns: title, snippet, and URL for each result."""
        from shared.tools.web_search import web_search as _web_search

        results = _web_search(query=query, max_results=max_results)
        lines = []
        for i, r in enumerate(results.results, 1):
            lines.append(f"{i}. {r.title}\n   {r.body}\n   URL: {r.href}")
        return "\n\n".join(lines) if lines else "No results found."

    return web_search


def _run_with_openai(task: str) -> TaskResult:
    """Use OpenAI agent with web search tool."""
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=0,
    )
    tools = [_create_web_search_tool()]
    system = (
        "You have access to web_search. ALWAYS use it for price comparisons, product info, or current data. "
        "For price comparisons: run separate searches per retailer (e.g. 'iPhone 15 Amazon', 'iPhone 15 Flipkart'). "
        "Format results as a markdown table when asked for tabular data. Use real search results only."
    )
    agent = create_agent(model=llm, tools=tools, system_prompt=system)
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})
    content = ""
    messages = result.get("messages") or []
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content and getattr(msg, "type", "") == "ai":
            content = msg.content
            break
    return TaskResult(result=content or f"Result for: {task}")


def _run_fallback(task: str) -> TaskResult:
    """Fallback when OpenAI not configured."""
    return TaskResult(result=f"General task received. (Set OPENAI_API_KEY for LLM execution): {task}")


def run_general_agent(task: str) -> TaskResult:
    """Execute general agent (OpenAI + web search) for any task.

    Uses real web search for price comparisons, product info, etc.

    Args:
        task: Task message or query.

    Returns:
        Structured TaskResult from the agent.
    """
    if os.getenv("OPENAI_API_KEY"):
        return _run_with_openai(task)
    return _run_fallback(task)
