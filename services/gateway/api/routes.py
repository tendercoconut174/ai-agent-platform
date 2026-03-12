"""API routes for the gateway service."""

import base64
import re
from typing import Any, Dict, Union

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.gateway.api.orchestrator_client import call_orchestrator
from shared.models import MessageRequest

router = APIRouter()


def _infer_output_format(message: str, explicit_format: str) -> str:
    """Infer output format from message when user says 'give me pdf' etc. but didn't pass output_format."""
    if explicit_format != "json":
        return explicit_format
    msg = message.lower()
    if any(p in msg for p in ("give me pdf", "in pdf", "as pdf", "pdf format", "output as pdf", "return pdf")):
        return "pdf"
    if any(p in msg for p in ("give me excel", "in excel", "as xl", "spreadsheet", "excel format", "return excel")):
        return "xl"
    return explicit_format


def _strip_format_hints(message: str, output_format: str) -> str:
    """Remove format-related phrases so the agent fetches data, not searches for existing files."""
    if output_format == "json":
        return message
    # Remove phrases that would confuse the agent into searching for PDF/Excel files
    patterns = [
        r"\bgive me (pdf|excel|xl)\s*",
        r"\bin (pdf|excel|xl) (format\s*)?",
        r"\bas (pdf|excel|xl)\s*",
        r"\b(pdf|excel|xl) (format\s*)?(of\s*)?",
        r"\breturn (as\s+)?(pdf|excel|xl)\s*",
        r"\boutput as (pdf|excel|xl)\s*",
    ]
    result = message
    for p in patterns:
        result = re.sub(p, " ", result, flags=re.IGNORECASE)
    return " ".join(result.split()).strip() or message


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


# File formats that trigger download; others return JSON
FILE_FORMATS = {"pdf", "xl"}


@router.post("/message", response_model=None)
def message(payload: MessageRequest) -> Union[Dict[str, Any], Response]:
    """Process a message by forwarding to Orchestrator.

    Flow: Gateway → Supervisor → Planner → Task Graph Engine → Queue → Workers → Tools → Delivery → User

    When output_format is pdf or xl, returns the file for download with Content-Disposition: attachment.
    Otherwise returns JSON.

    Args:
        payload: Message request with user message.

    Returns:
        JSON result or file download (Response).
    """
    try:
        output_format = _infer_output_format(payload.message, payload.output_format)
        message = _strip_format_hints(payload.message, output_format)
        data = call_orchestrator(
            message,
            output_format=output_format,
            mode=payload.mode,
        )
        # Return file for download when output is a file format
        if output_format in FILE_FORMATS and data.get("content_base64") and data.get("content_type"):
            raw = base64.b64decode(data["content_base64"])
            ext = "xlsx" if output_format == "xl" else output_format
            filename = data.get("filename") or f"result.{ext}"
            return Response(
                content=raw,
                media_type=data["content_type"],
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        return data
    except Exception as e:
        detail = _extract_orchestrator_error(e)
        raise HTTPException(status_code=502, detail=f"Orchestrator error: {detail}")
