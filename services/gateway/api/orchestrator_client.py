"""Async client for calling the Orchestrator service."""

import json
import logging
import os
from collections.abc import AsyncGenerator
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
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Call orchestrator /orchestrate endpoint asynchronously."""
    payload: dict[str, object] = {
        "message": message,
        "output_format": output_format,
        "mode": mode,
        "session_id": session_id,
        "callback_url": callback_url,
        "conversation_history": conversation_history or [],
    }
    if workflow_id:
        payload["workflow_id"] = workflow_id
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/orchestrate",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def stream_orchestrator(
    message: str,
    timeout: float = 120.0,
    output_format: str = "json",
    mode: str = "auto",
    session_id: str | None = None,
    callback_url: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    workflow_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream orchestrator /orchestrate/stream endpoint (SSE)."""
    payload: dict[str, object] = {
        "message": message,
        "output_format": output_format,
        "mode": mode,
        "session_id": session_id,
        "callback_url": callback_url,
        "conversation_history": conversation_history or [],
    }
    if workflow_id:
        payload["workflow_id"] = workflow_id

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{ORCHESTRATOR_URL}/orchestrate/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]" or not data.strip():
                        continue
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        pass
