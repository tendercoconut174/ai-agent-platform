"""Supervisor agent: orchestrates the full workflow."""

from typing import Any, Dict, Optional, Tuple

from services.orchestrator.supervisor.supervisor_logic import run_supervisor


def orchestrate(user_message: str, timeout: int = 30) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Orchestrate full workflow: Supervisor → Planner → Task Graph Engine → Queue → Workers.

    Args:
        user_message: User message or goal.
        timeout: Seconds to wait per task.

    Returns:
        Tuple of (result dict or None, workflow_id or None).
    """
    return run_supervisor(user_message, timeout=timeout)
