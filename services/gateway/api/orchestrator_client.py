"""Client for calling the Orchestrator service."""

import os
from typing import Any, Dict

import httpx

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")


def call_orchestrator(
    message: str,
    timeout: float = 60.0,
    output_format: str = "json",
    mode: str = "auto",
) -> Dict[str, Any]:
    """Call orchestrator /orchestrate endpoint.

    Args:
        message: User message.
        timeout: Request timeout in seconds.
        output_format: json, pdf, or xl.
        mode: auto, chat, or task.

    Returns:
        Response dict from orchestrator.
    """
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{ORCHESTRATOR_URL}/orchestrate",
            json={
                "message": message,
                "output_format": output_format,
                "mode": mode,
            },
        )
        response.raise_for_status()
        return response.json()
