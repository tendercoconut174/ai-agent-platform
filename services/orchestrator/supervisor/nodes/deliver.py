"""Deliver node – formats the final result for output."""

import logging

from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)


MAX_RESULT_LENGTH = 100_000  # Safety limit for delivery


async def deliver(state: WorkflowState) -> WorkflowState:
    """Format the final result. The actual file conversion (PDF, Excel, etc.)
    is handled downstream by the delivery service."""
    if state.get("needs_code_approval", False):
        final_result = "Code execution requires your approval. Please review the code below and approve in the UI to run it."
        logger.info("[deliver] needs_code_approval | approval_id=%s | workflow=%s",
                    state.get("pending_code_approval_id"), state.get("workflow_id", "?"))
        return {**state, "final_result": final_result}

    final_result = state.get("final_result", "")
    error = state.get("error")

    if error and not final_result:
        final_result = f"I encountered an error: {error}"

    if not final_result:
        final_result = "I wasn't able to produce a result. Could you rephrase your request?"

    # Output validation: truncate if excessively long
    if len(final_result) > MAX_RESULT_LENGTH:
        final_result = final_result[:MAX_RESULT_LENGTH] + "\n\n[Output truncated for length.]"
        logger.warning("[deliver] Result truncated from %d to %d chars", len(state.get("final_result", "")), MAX_RESULT_LENGTH)

    logger.info("[deliver] result_len=%d | format=%s | workflow=%s | iterations=%d",
                len(final_result), state.get("output_format", "json"),
                state.get("workflow_id", "?"), state.get("iteration_count", 0))
    return {**state, "final_result": final_result}
