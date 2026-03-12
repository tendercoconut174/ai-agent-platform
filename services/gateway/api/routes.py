"""API routes for the gateway service."""

from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException

from services.gateway.api.orchestrator_client import call_orchestrator
from shared.models import MessageRequest

router = APIRouter()


def _extract_orchestrator_error(exc: Exception) -> str:
    """Extract meaningful error detail from Orchestrator failure."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        try:
            body = exc.response.json()
            if isinstance(body, dict) and "detail" in body:
                return str(body["detail"])
        except Exception:
            pass
    return str(exc)


@router.post("/message")
def message(payload: MessageRequest) -> Dict[str, Any]:
    """Process a message by forwarding to Orchestrator.

    Flow: Gateway → Supervisor → Planner → Task Graph Engine → Queue → Workers → Tools → Delivery → User

    Args:
        payload: Message request with user message.

    Returns:
        Result from Delivery Service.
    """
    try:
        return call_orchestrator(payload.message)
    except Exception as e:
        detail = _extract_orchestrator_error(e)
        raise HTTPException(status_code=502, detail=f"Orchestrator error: {detail}")
