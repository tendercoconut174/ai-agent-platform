"""Supervisor agent: orchestrates the full workflow."""

from typing import Any, Dict, Optional, Tuple

from services.orchestrator.supervisor.supervisor_logic import run_supervisor


def orchestrate(
    user_message: str,
    timeout: int = 30,
    mode: str = "auto",
    output_format: str = "json",
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Orchestrate full workflow or direct chat.

    Args:
        user_message: User message or goal.
        timeout: Seconds to wait per task.
        mode: 'auto' (classify), 'chat' (direct chat), or 'task' (full planning).
        output_format: json, pdf, or xl. Planner adds format instructions for pdf/xl.

    Returns:
        Tuple of (result dict or None, workflow_id or None).
    """
    return run_supervisor(
        user_message,
        timeout=timeout,
        mode=mode,
        output_format=output_format,
    )
