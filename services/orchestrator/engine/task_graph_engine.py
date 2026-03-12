"""Task Graph Engine: executes task graphs and pushes to queue."""

from typing import Any, Dict, List, Optional

from platform_queue.task_queue import enqueue_task, wait_for_result
from shared.models import TaskGraph, TaskNode, TaskPayload


def execute_graph(graph: TaskGraph, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Execute task graph by pushing nodes to queue and collecting results.

    Args:
        graph: Task graph from Planner.
        timeout: Seconds to wait per task.

    Returns:
        Final result dict, or None on timeout.
    """
    results: Dict[str, Any] = {}
    for node in graph.nodes:
        task_id = f"{graph.workflow_id}:{node.node_id}"
        payload = TaskPayload(
            task_id=task_id,
            message=node.message,
            task_type=node.task_type,
        )
        enqueue_task(payload)
        result = wait_for_result(task_id, timeout=timeout)
        if result is None:
            return None
        results[node.node_id] = result
    return _get_final_result(graph.nodes, results)


def _get_final_result(nodes: List[TaskNode], results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract final result from node results."""
    if not nodes:
        return {"result": ""}
    last_node = nodes[-1]
    return results.get(last_node.node_id, {"result": ""})
