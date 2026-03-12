"""Supervisor logic: coordinates Planner and Task Graph Engine."""

from typing import Any, Dict, Optional, Tuple

from services.orchestrator.engine.task_graph_engine import execute_graph
from services.orchestrator.planner.planner import plan
from shared.models import TaskGraph


def run_supervisor(user_message: str, timeout: int = 30) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Run supervisor workflow: plan → execute graph.

    Args:
        user_message: User message or goal.
        timeout: Seconds to wait per task.

    Returns:
        Tuple of (result dict or None, workflow_id or None).
    """
    task_graph = plan(user_message)
    result = execute_graph(task_graph, timeout=timeout)
    return (result, task_graph.workflow_id)
