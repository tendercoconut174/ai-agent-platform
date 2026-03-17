"""Evaluate node – checks if the goal is achieved via structured LLM output."""

import logging
import time

from pydantic import BaseModel, Field

from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)


class Evaluation(BaseModel):
    """Structured evaluation result from the LLM."""

    achieved: bool = Field(description="Whether the result achieves the user's goal")
    reasoning: str = Field(description="Brief explanation of why the goal is or is not achieved")


EVAL_SYSTEM = (
    "You are a quality evaluator for an AI agent platform. "
    "Determine whether the provided result achieves the user's original goal.\n\n"
    "Guidelines:\n"
    "- If the result substantially answers or fulfills the goal, mark achieved=true.\n"
    "- If the result is missing key information, is an error, or is off-topic, mark achieved=false.\n"
    "- Be lenient: partial but useful results should be accepted.\n"
    "- A result that acknowledges it cannot find information is still considered achieved "
    "if the search was reasonable.\n"
    "- For simple/casual intents, prefer achieved=true when the result is relevant and complete."
)


async def _evaluate_with_llm(goal: str, result: str, intent: str = "simple") -> tuple[bool, str]:
    """Evaluate using structured LLM output. Returns (achieved, reasoning)."""
    from shared.llm import get_llm

    llm = get_llm("evaluator", temperature=0)
    structured_llm = llm.with_structured_output(Evaluation)

    user_content = f"Goal: {goal}\n\nResult (first 2000 chars):\n{result[:2000]}"
    if intent:
        user_content += f"\n\n(Intent was: {intent} – use for context when deciding.)"

    evaluation: Evaluation = await structured_llm.ainvoke([
        {"role": "system", "content": EVAL_SYSTEM},
        {"role": "user", "content": user_content},
    ])

    return evaluation.achieved, evaluation.reasoning


async def evaluate(state: WorkflowState) -> WorkflowState:
    """Evaluate if the goal is achieved via structured LLM output."""
    t0 = time.perf_counter()
    if state.get("needs_code_approval", False):
        logger.info("[evaluate] DONE  | needs_code_approval, passing to deliver | %.2fs", time.perf_counter() - t0)
        return state

    goal = state.get("goal", "")
    final_result = state.get("final_result", "")
    iteration = state.get("iteration_count", 0) + 1
    max_iter = state.get("max_iterations", 5)
    deadline = state.get("deadline", float("inf"))

    logger.info("[evaluate] START | iteration=%d/%d | result_len=%d", iteration, max_iter, len(final_result or ""))

    if iteration >= max_iter:
        logger.info("[evaluate] DONE  | max iterations reached, accepting | %.2fs", time.perf_counter() - t0)
        return {**state, "iteration_count": iteration, "goal_achieved": True}

    remaining = deadline - time.perf_counter()
    if remaining < 15:
        logger.warning("[evaluate] DONE  | deadline approaching (%.1fs left), accepting current result | %.2fs", remaining, time.perf_counter() - t0)
        return {**state, "iteration_count": iteration, "goal_achieved": True}

    if not final_result or state.get("error"):
        logger.info("[evaluate] DONE  | no result or error, goal NOT achieved | %.2fs", time.perf_counter() - t0)
        return {**state, "iteration_count": iteration, "goal_achieved": False}

    from shared.llm import is_llm_available

    intent = state.get("intent", "simple")
    if is_llm_available("evaluator"):
        achieved, reasoning = await _evaluate_with_llm(goal, final_result, intent)
        logger.info("[evaluate] DONE  | goal_achieved=%s | reason=%s | %.2fs", achieved, reasoning[:100], time.perf_counter() - t0)
    else:
        achieved = bool(final_result and len(final_result) > 20)
        logger.info("[evaluate] DONE  | goal_achieved=%s (no LLM, heuristic) | %.2fs", achieved, time.perf_counter() - t0)

    return {**state, "iteration_count": iteration, "goal_achieved": achieved}
