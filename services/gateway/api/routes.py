"""Gateway API routes – async /message, /message/upload (multipart)."""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Any, Optional, Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from services.gateway.api.orchestrator_client import call_orchestrator, stream_orchestrator
from shared.rate_limit import rate_limit_dep
from services.gateway.input_processor import build_message
from services.gateway.pending_clarification_manager import (
    load_and_clear_pending_clarification,
    save_pending_clarification,
)
from shared.pending_code_approval_manager import (
    load_and_clear_pending_code_approval,
    save_pending_code_approval_by_id,
)
from services.gateway.session_manager import add_message, get_history, get_or_create_session
from shared.models.schemas import MessageRequest

logger = logging.getLogger(__name__)
router = APIRouter()

FILE_FORMATS = {"pdf", "xl", "audio"}

FORMAT_PATTERNS = {
    "pdf": ["give me pdf", "in pdf", "as pdf", "pdf format", "output as pdf", "return pdf"],
    "xl": ["give me excel", "in excel", "as xl", "spreadsheet", "excel format", "return excel"],
}

STRIP_PATTERNS = [
    r"\bgive me (pdf|excel|xl)\s*",
    r"\bin (pdf|excel|xl) (format\s*)?",
    r"\bas (pdf|excel|xl)\s*",
    r"\b(pdf|excel|xl) (format\s*)?(of\s*)?",
    r"\breturn (as\s+)?(pdf|excel|xl)\s*",
    r"\boutput as (pdf|excel|xl)\s*",
]


def _infer_output_format(message: str, explicit: str) -> str:
    if explicit != "json":
        return explicit
    msg = message.lower()
    for fmt, patterns in FORMAT_PATTERNS.items():
        if any(p in msg for p in patterns):
            return fmt
    return explicit


def _strip_format_hints(message: str, fmt: str) -> str:
    if fmt == "json":
        return message
    result = message
    for p in STRIP_PATTERNS:
        result = re.sub(p, " ", result, flags=re.IGNORECASE)
    return " ".join(result.split()).strip() or message


def _extract_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        try:
            body = exc.response.json()
            if isinstance(body, dict) and "detail" in body:
                return str(body["detail"])
        except Exception:
            pass
    return str(exc)


@router.post("/message", response_model=None)
async def message_endpoint(
    payload: MessageRequest,
    _: None = Depends(rate_limit_dep),
) -> Union[dict[str, Any], Response]:
    """Async message endpoint – sends to orchestrator, waits for result.

    Returns JSON or file download depending on output_format.
    Supports human-in-the-loop: when the orchestrator needs clarification,
    returns needs_clarification=true. User can resume by sending a follow-up
    with workflow_id.
    """
    t0 = time.perf_counter()
    logger.info("[gateway] POST /message received | message=%s | workflow_id=%s",
                payload.message[:120], payload.workflow_id)
    try:
        session_id, created = await asyncio.to_thread(get_or_create_session, payload.session_id)
        logger.info("[gateway] Session %s (%s)", session_id, "new" if created else "existing")

        # Code approval resume: run approved code, then send output to orchestrator
        message_to_send = payload.message
        output_format_override = payload.output_format
        require_code_approval = payload.require_code_approval

        if payload.code_approval_id:
            pending = await asyncio.to_thread(
                load_and_clear_pending_code_approval,
                payload.code_approval_id,
            )
            if pending:
                from shared.mcp.tools.code_executor import execute_python
                result = await asyncio.to_thread(execute_python, pending.code)
                output = ""
                if result.get("stdout"):
                    output += result["stdout"]
                if result.get("stderr"):
                    output += f"\nSTDERR: {result['stderr']}"
                if result.get("error"):
                    output += f"\nERROR: {result['error']}"
                output = output.strip() or "(no output)"
                has_error = not result.get("success", True) or result.get("error") or result.get("stderr")
                if has_error:
                    message_to_send = (
                        f"[Code approved and executed – EXCEPTION/ERROR occurred]\n\n"
                        f"Error output:\n{output}\n\n"
                        f"Original request: {pending.original_goal}\n\n"
                        f"Fix the code and run it again. Use execute_python to run your fix – do not ask for approval, "
                        f"run it directly. If it succeeds, analyze the output and provide the final answer. "
                        f"If you cannot fix it after trying, explain the issue to the user."
                    )
                else:
                    message_to_send = (
                        f"[Code approved and executed]\n\nOutput:\n{output}\n\n"
                        f"Original request: {pending.original_goal}\n\n"
                        f"Please analyze the output and provide the final answer to the user."
                    )
                output_format_override = pending.output_format
                require_code_approval = False
                logger.info("[gateway] Resuming with code approval | has_error=%s | output_len=%d", has_error, len(output))
            else:
                logger.warning("[gateway] code_approval_id=%s not found; returning error to break loop", payload.code_approval_id)
                session_id, _ = await asyncio.to_thread(get_or_create_session, payload.session_id)
                await asyncio.to_thread(add_message, session_id, "user", payload.message)
                await asyncio.to_thread(add_message, session_id, "assistant", "This code approval has already been used or expired. Please send your original request again.")
                return {
                    "result": "This code approval has already been used or expired. Please send your original request again (without clicking Approve again).",
                    "workflow_id": None,
                    "output_format": payload.output_format,
                    "session_id": session_id,
                    "needs_clarification": False,
                    "needs_code_approval": False,
                }

        if payload.workflow_id and not payload.code_approval_id:
            pending = await asyncio.to_thread(
                load_and_clear_pending_clarification,
                payload.workflow_id,
            )
            if pending:
                message_to_send = (
                    f"{pending.original_goal}\n\n[User clarification] {payload.message}"
                )
                output_format_override = pending.output_format
                logger.info("[gateway] Resuming workflow %s with clarification | merged goal=%s",
                            payload.workflow_id, message_to_send[:120])
            else:
                logger.warning(
                    "[gateway] workflow_id=%s provided but no pending clarification found; "
                    "treating as new message. Use workflow_id from the most recent needs_clarification response.",
                    payload.workflow_id,
                )

        await asyncio.to_thread(add_message, session_id, "user", payload.message)

        output_format = _infer_output_format(message_to_send, output_format_override)
        clean_message = _strip_format_hints(message_to_send, output_format)
        history = await asyncio.to_thread(get_history, session_id, 20)
        logger.info("[gateway] Inferred format=%s | mode=%s | history=%d msgs | forwarding to orchestrator",
                     output_format, payload.mode, len(history))

        data = await call_orchestrator(
            message=clean_message,
            output_format=output_format,
            mode=payload.mode,
            session_id=session_id,
            callback_url=payload.callback_url,
            conversation_history=history,
            workflow_id=payload.workflow_id if not payload.code_approval_id else None,
            require_code_approval=require_code_approval,
        )
        elapsed = time.perf_counter() - t0
        logger.info("[gateway] Orchestrator responded in %.2fs", elapsed)

        if isinstance(data, dict):
            data["session_id"] = session_id
            await asyncio.to_thread(add_message, session_id, "assistant", data.get("result", ""))

            # Human-in-the-loop: save pending clarification for resume
            if data.get("needs_clarification") and data.get("workflow_id"):
                await asyncio.to_thread(
                    save_pending_clarification,
                    workflow_id=data["workflow_id"],
                    session_id=session_id,
                    original_goal=clean_message,
                    question=data.get("question", data.get("result", "")),
                    output_format=output_format,
                )
                logger.info("[gateway] Saved pending clarification for workflow %s", data["workflow_id"])

            # Human-in-the-loop: save pending code approval locally (gateway and orchestrator are
            # separate processes; in-memory storage is not shared, so gateway must save when it receives)
            if data.get("needs_code_approval") and data.get("code_approval_id"):
                await asyncio.to_thread(
                    save_pending_code_approval_by_id,
                    approval_id=data["code_approval_id"],
                    workflow_id=data.get("workflow_id", ""),
                    session_id=session_id,
                    code=data.get("code", ""),
                    step_id=data.get("step_id", "step_1"),
                    original_goal=data.get("original_goal", clean_message),
                    output_format=data.get("output_format", output_format),
                )
                logger.info("[gateway] Saved pending code approval locally for approval_id=%s", data["code_approval_id"])

        if output_format in FILE_FORMATS and data.get("content_base64") and data.get("content_type"):
            raw = base64.b64decode(data["content_base64"])
            ext = "xlsx" if output_format == "xl" else output_format
            filename = data.get("filename") or f"result.{ext}"
            logger.info("[gateway] Returning file download: %s (%d bytes) | total=%.2fs", filename, len(raw), time.perf_counter() - t0)
            return Response(
                content=raw,
                media_type=data["content_type"],
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        logger.info("[gateway] Returning JSON response | total=%.2fs", time.perf_counter() - t0)
        return data
    except Exception as e:
        elapsed = time.perf_counter() - t0
        detail = _extract_error(e)
        logger.error("[gateway] Request failed after %.2fs: %s", elapsed, detail)
        raise HTTPException(status_code=502, detail=f"Orchestrator error: {detail}")


@router.post("/message/upload", response_model=None)
async def message_upload_endpoint(
    message: Optional[str] = Form(None),
    output_format: str = Form("json"),
    mode: str = Form("auto"),
    session_id: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    files: Optional[list[UploadFile]] = File(None),
    _: None = Depends(rate_limit_dep),
) -> Union[dict[str, Any], Response]:
    """Multipart upload endpoint – accepts text, audio, images, and file attachments.

    Audio is transcribed via Whisper, images described via GPT-4 Vision,
    files have text extracted. All combined into a single message for the orchestrator.
    """
    try:
        combined = await build_message(text=message, audio=audio, image=image, files=files)
        if not combined:
            raise HTTPException(status_code=400, detail="No input provided")

        fmt = _infer_output_format(combined, output_format)
        clean = _strip_format_hints(combined, fmt)
        data = await call_orchestrator(message=clean, output_format=fmt, mode=mode, session_id=session_id)

        if fmt in FILE_FORMATS and data.get("content_base64") and data.get("content_type"):
            raw = base64.b64decode(data["content_base64"])
            ext = "xlsx" if fmt == "xl" else fmt
            filename = data.get("filename") or f"result.{ext}"
            return Response(
                content=raw,
                media_type=data["content_type"],
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        detail = _extract_error(e)
        raise HTTPException(status_code=502, detail=f"Orchestrator error: {detail}")


@router.post("/message/stream")
async def message_stream_endpoint(
    payload: MessageRequest,
    _: None = Depends(rate_limit_dep),
) -> EventSourceResponse:
    """Stream workflow progress via Server-Sent Events. Live steps and results."""
    async def event_generator():
        session_id = None
        try:
            session_id, _ = await asyncio.to_thread(get_or_create_session, payload.session_id)
            message_to_send = payload.message
            output_format_override = payload.output_format
            require_code_approval = payload.require_code_approval

            if payload.code_approval_id:
                pending = await asyncio.to_thread(
                    load_and_clear_pending_code_approval,
                    payload.code_approval_id,
                )
                if pending:
                    from shared.mcp.tools.code_executor import execute_python
                    result = await asyncio.to_thread(execute_python, pending.code)
                    output = (result.get("stdout") or "") + (f"\nSTDERR: {result.get('stderr')}" if result.get("stderr") else "") + (f"\nERROR: {result.get('error')}" if result.get("error") else "")
                    output = output.strip() or "(no output)"
                    has_error = not result.get("success", True) or result.get("error") or result.get("stderr")
                    if has_error:
                        message_to_send = (
                            f"[Code approved and executed – EXCEPTION/ERROR occurred]\n\n"
                            f"Error output:\n{output}\n\n"
                            f"Original request: {pending.original_goal}\n\n"
                            f"Fix the code and run it again. Use execute_python to run your fix – do not ask for approval, "
                            f"run it directly. If it succeeds, analyze the output and provide the final answer. "
                            f"If you cannot fix it after trying, explain the issue to the user."
                        )
                    else:
                        message_to_send = (
                            f"[Code approved and executed]\n\nOutput:\n{output}\n\n"
                            f"Original request: {pending.original_goal}\n\n"
                            f"Please analyze the output and provide the final answer to the user."
                        )
                    output_format_override = pending.output_format
                    require_code_approval = False
                else:
                    logger.warning("[gateway] code_approval_id=%s not found; returning error to break loop", payload.code_approval_id)
                    await asyncio.to_thread(add_message, session_id, "user", payload.message)
                    err_msg = "This code approval has already been used or expired. Please send your original request again (without clicking Approve again)."
                    await asyncio.to_thread(add_message, session_id, "assistant", err_msg)
                    yield {"data": json.dumps({
                        "type": "done",
                        "workflow_id": None,
                        "session_id": session_id,
                        "needs_clarification": False,
                        "needs_code_approval": False,
                        "delivery": {"result": err_msg, "needs_clarification": False, "needs_code_approval": False},
                    })}
                    return

            if payload.workflow_id and not payload.code_approval_id:
                pending = await asyncio.to_thread(
                    load_and_clear_pending_clarification,
                    payload.workflow_id,
                )
                if pending:
                    message_to_send = f"{pending.original_goal}\n\n[User clarification] {payload.message}"
                    output_format_override = pending.output_format

            await asyncio.to_thread(add_message, session_id, "user", payload.message)
            output_format = _infer_output_format(message_to_send, output_format_override)
            clean_message = _strip_format_hints(message_to_send, output_format)
            history = await asyncio.to_thread(get_history, session_id, 20)

            async for event in stream_orchestrator(
                message=clean_message,
                output_format=output_format,
                mode=payload.mode,
                session_id=session_id,
                conversation_history=history,
                workflow_id=payload.workflow_id if not payload.code_approval_id else None,
                require_code_approval=require_code_approval,
            ):
                event["session_id"] = session_id
                if event.get("type") == "done":
                    delivery = event.get("delivery", {})
                    result_text = delivery.get("result", "")
                    await asyncio.to_thread(add_message, session_id, "assistant", result_text)
                    if delivery.get("needs_clarification") and delivery.get("workflow_id"):
                        await asyncio.to_thread(
                            save_pending_clarification,
                            workflow_id=delivery["workflow_id"],
                            session_id=session_id,
                            original_goal=clean_message,
                            question=delivery.get("question", result_text),
                            output_format=output_format,
                        )
                    if delivery.get("needs_code_approval") and delivery.get("code_approval_id"):
                        await asyncio.to_thread(
                            save_pending_code_approval_by_id,
                            approval_id=delivery["code_approval_id"],
                            workflow_id=delivery.get("workflow_id", ""),
                            session_id=session_id,
                            code=delivery.get("code", ""),
                            step_id=delivery.get("step_id", "step_1"),
                            original_goal=delivery.get("original_goal", clean_message),
                            output_format=delivery.get("output_format", output_format),
                        )
                        logger.info("[gateway] Saved pending code approval locally for approval_id=%s", delivery["code_approval_id"])
                yield {"data": json.dumps(event)}
        except Exception as e:
            logger.exception("[gateway] Stream failed: %s", e)
            yield {"data": json.dumps({"type": "error", "error": str(e), "session_id": session_id})}

    return EventSourceResponse(event_generator())
