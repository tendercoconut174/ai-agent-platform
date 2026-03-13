"""Async client for calling the Orchestrator service."""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")


async def call_orchestrator(
    message: str,
    timeout: float = 120.0,
    output_format: str = "json",
    mode: str = "auto",
    session_id: str | None = None,
    callback_url: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Call orchestrator /orchestrate endpoint asynchronously."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/orchestrate",
            json={
                "message": message,
                "output_format": output_format,
                "mode": mode,
                "session_id": session_id,
                "callback_url": callback_url,
                "conversation_history": conversation_history or [],
            },
        )
        response.raise_for_status()
        return response.json()
