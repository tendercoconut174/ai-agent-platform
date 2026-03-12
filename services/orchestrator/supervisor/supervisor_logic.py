"""Supervisor logic: coordinates Planner and Task Graph Engine."""

from typing import Any, Dict, Optional, Tuple

from services.orchestrator.chat.classifier import classify_intent
from services.orchestrator.chat.direct_chat import direct_chat
from services.orchestrator.engine.task_graph_engine import execute_graph
from services.orchestrator.planner.planner import plan
from shared.models import TaskGraph


def run_supervisor(
    user_message: str,
    timeout: int = 30,
    mode: str = "auto",
    output_format: str = "json",
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Run supervisor workflow: plan → execute graph, or direct chat for casual messages.

    Args:
        user_message: User message or goal.
        timeout: Seconds to wait per task.
        mode: 'auto' (classify), 'chat' (direct chat), or 'task' (full planning).
        output_format: json, pdf, or xl. Planner adds format instructions for pdf/xl.

    Returns:
        Tuple of (result dict or None, workflow_id or None).
    """
    if mode == "chat":
        response = direct_chat(user_message)
        return ({"result": response}, None)

    if mode == "auto":
        intent = classify_intent(user_message)
        if intent == "casual":
            response = direct_chat(user_message)
            return ({"result": response}, None)

    # mode == "task" or intent == "complex"
    task_graph = plan(user_message, output_format=output_format)
    result = execute_graph(task_graph, timeout=timeout)
    return (result, task_graph.workflow_id)
