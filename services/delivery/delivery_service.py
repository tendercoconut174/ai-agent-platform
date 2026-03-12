"""Delivery Service: formats and delivers results to user."""

from typing import Any, Dict, Optional

from shared.models import OrchestratorResponse


def deliver(
    result: Optional[Dict[str, Any]],
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Format result for delivery to user.

    Args:
        result: Result dict from Task Graph Engine.
        workflow_id: Optional workflow identifier.

    Returns:
        Formatted response for user.
    """
    if result is None:
        return {"status": "timeout", "result": "Request timed out"}
    response = OrchestratorResponse(
        result=result.get("result", ""),
        workflow_id=workflow_id,
    )
    return response.model_dump()
