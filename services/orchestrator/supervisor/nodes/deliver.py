"""Deliver node – formats the final result for output."""

import logging

from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)


async def deliver(state: WorkflowState) -> WorkflowState:
    """Format the final result. The actual file conversion (PDF, Excel, etc.)
    is handled downstream by the delivery service."""
    final_result = state.get("final_result", "")
    error = state.get("error")

    if error and not final_result:
        final_result = f"I encountered an error: {error}"

    if not final_result:
        final_result = "I wasn't able to produce a result. Could you rephrase your request?"

    logger.info("[deliver] result_len=%d | format=%s | workflow=%s | iterations=%d",
                len(final_result), state.get("output_format", "json"),
                state.get("workflow_id", "?"), state.get("iteration_count", 0))
    return {**state, "final_result": final_result}
