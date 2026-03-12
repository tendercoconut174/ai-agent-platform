"""Planner Agent: OpenAI agent that plans actions and creates task graphs."""

import os
import uuid
import warnings

# Suppress LangChain Pydantic v1 + Python 3.14 compatibility warning
warnings.filterwarnings(
    "ignore",
    message=".*Pydantic V1.*Python 3.14.*",
    category=UserWarning,
)

from shared.models import TaskGraph, TaskNode


# Format instructions for output_format so the agent produces data the delivery tools can consume
_FORMAT_INSTRUCTIONS = {
    "xl": (
        " CRITICAL: You MUST format your final response as a markdown table. "
        "Use | for column separators. Example: | Column1 | Column2 |\n|--------|--------|\n| val1 | val2 |. "
        "All tabular/list data must be in this table format."
    ),
    "pdf": (
        " CRITICAL: Format your response for document export. Use clear ## headings, "
        "structured lists, and readable paragraphs. Avoid raw URLs; use descriptive text."
    ),
    "json": "",
}


def _plan_with_openai(user_message: str, output_format: str = "json") -> TaskGraph:
    """Use OpenAI Planner Agent."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=0,
    )
    prompt = f"""Plan a task. Reply ONLY: task_type|message (task_type: research, summarize, or general)
User goal: {user_message}"""
    response = llm.invoke(prompt)
    content = (response.content or "general|" + user_message).strip()
    parts = content.split("|", 1)
    task_type = (parts[0].strip().lower() if parts else "general")[:20]
    message = (parts[1].strip() if len(parts) > 1 else user_message) or user_message
    if task_type not in ("research", "summarize"):
        task_type = "research" if "research" in user_message.lower() else "general"
    # Append format instructions so agent output works with delivery tools
    message += _FORMAT_INSTRUCTIONS.get(output_format, "")
    return TaskGraph(
        workflow_id=str(uuid.uuid4()),
        nodes=[TaskNode(node_id="task_1", task_type=task_type, message=message, dependencies=[])],
    )


def _plan_fallback(user_message: str, output_format: str = "json") -> TaskGraph:
    """Fallback when OpenAI not configured."""
    task_type = "research" if "research" in user_message.lower() else "general"
    message = user_message + _FORMAT_INSTRUCTIONS.get(output_format, "")
    return TaskGraph(
        workflow_id=str(uuid.uuid4()),
        nodes=[TaskNode(node_id="task_1", task_type=task_type, message=message, dependencies=[])],
    )


def plan(user_message: str, output_format: str = "json") -> TaskGraph:
    """Planner Agent: convert user goal into task graph (DAG).

    Uses OpenAI when OPENAI_API_KEY is set; otherwise rule-based fallback.
    When output_format is pdf or xl, appends format instructions so agent output
    works with delivery tools.

    Args:
        user_message: User message or goal.
        output_format: json, pdf, or xl. Planner adds format-specific instructions.

    Returns:
        TaskGraph with nodes to execute.
    """
    if os.getenv("OPENAI_API_KEY"):
        return _plan_with_openai(user_message, output_format=output_format)
    return _plan_fallback(user_message, output_format=output_format)
