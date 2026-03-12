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


def _plan_with_openai(user_message: str) -> TaskGraph:
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
    return TaskGraph(
        workflow_id=str(uuid.uuid4()),
        nodes=[TaskNode(node_id="task_1", task_type=task_type, message=message, dependencies=[])],
    )


def _plan_fallback(user_message: str) -> TaskGraph:
    """Fallback when OpenAI not configured."""
    task_type = "research" if "research" in user_message.lower() else "general"
    return TaskGraph(
        workflow_id=str(uuid.uuid4()),
        nodes=[TaskNode(node_id="task_1", task_type=task_type, message=user_message, dependencies=[])],
    )


def plan(user_message: str) -> TaskGraph:
    """Planner Agent: convert user goal into task graph (DAG).

    Uses OpenAI when OPENAI_API_KEY is set; otherwise rule-based fallback.

    Args:
        user_message: User message or goal.

    Returns:
        TaskGraph with nodes to execute.
    """
    if os.getenv("OPENAI_API_KEY"):
        return _plan_with_openai(user_message)
    return _plan_fallback(user_message)
