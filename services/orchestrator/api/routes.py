"""Orchestrator API routes."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.delivery.delivery_service import deliver
from services.orchestrator.supervisor.supervisor_agent import orchestrate
from shared.models import OrchestratorRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/orchestrate")
def orchestrate_endpoint(payload: OrchestratorRequest) -> Dict[str, Any]:
    """Run full workflow: Supervisor → Planner → Task Graph Engine → Workers → Delivery.

    Args:
        payload: Orchestrator request with user message.

    Returns:
        Formatted result for user.
    """
    try:
        result, workflow_id = orchestrate(payload.message)
        return deliver(result, workflow_id)
    except Exception as e:
        logger.exception("Orchestrator failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
