"""Orchestrator API routes."""

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from services.delivery.delivery_service import deliver
from services.orchestrator.supervisor.graph import run_workflow, run_workflow_stream
from shared.models.schemas import OrchestratorRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/orchestrate")
async def orchestrate_endpoint(payload: OrchestratorRequest) -> dict[str, Any]:
    """Run the full supervisor workflow asynchronously and return formatted result."""
    t0 = time.perf_counter()
    logger.info("[orchestrator] Received goal=%s | format=%s | mode=%s", payload.message[:120], payload.output_format, payload.mode)
    try:
        state = await run_workflow(
            goal=payload.message,
            output_format=payload.output_format,
            session_id=payload.session_id,
            callback_url=payload.callback_url,
            conversation_history=payload.conversation_history,
        )
        workflow_elapsed = time.perf_counter() - t0
        workflow_id = state.get("workflow_id")

        # Human-in-the-loop: return clarification request without delivery formatting
        if state.get("needs_clarification"):
            question = state.get("clarification_question", "")
            logger.info("[orchestrator] Workflow %s needs clarification | question=%s | %.2fs",
                       workflow_id, question[:80], workflow_elapsed)
            return {
                "result": question,
                "workflow_id": workflow_id,
                "output_format": payload.output_format,
                "session_id": payload.session_id,
                "needs_clarification": True,
                "question": question,
            }

        result_text = state.get("final_result", "")
        logger.info("[orchestrator] Workflow %s completed in %.2fs | intent=%s | iterations=%d",
                     workflow_id, workflow_elapsed, state.get("intent", "?"), state.get("iteration_count", 0))

        t1 = time.perf_counter()
        response = await asyncio.to_thread(
            deliver,
            result={"result": result_text},
            workflow_id=workflow_id,
            output_format=payload.output_format,
        )
        # Include workflow metadata for UI (steps, intent)
        step_results = state.get("step_results") or []
        response["intent"] = state.get("intent")
        response["step_results"] = [
            {"node_id": r.node_id, "agent_type": r.agent_type, "result": (r.result or "")[:500], "error": r.error, "success": r.success}
            for r in step_results
        ]
        logger.info("[orchestrator] Delivery formatted in %.2fs | format=%s | total=%.2fs",
                     time.perf_counter() - t1, payload.output_format, time.perf_counter() - t0)
        return response
    except Exception as e:
        logger.exception("[orchestrator] Failed after %.2fs: %s", time.perf_counter() - t0, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orchestrate/stream")
async def orchestrate_stream_endpoint(payload: OrchestratorRequest) -> EventSourceResponse:
    """Stream workflow progress via Server-Sent Events."""
    async def event_generator():
        try:
            async for event in run_workflow_stream(
                goal=payload.message,
                output_format=payload.output_format,
                session_id=payload.session_id,
                callback_url=payload.callback_url,
                conversation_history=payload.conversation_history,
            ):
                yield {"data": json.dumps(event)}
        except Exception as e:
            logger.exception("[orchestrator] Stream failed: %s", e)
            yield {"data": json.dumps({"type": "error", "error": str(e)})}

    return EventSourceResponse(event_generator())
