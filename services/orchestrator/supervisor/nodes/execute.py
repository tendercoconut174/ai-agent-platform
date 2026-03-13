"""Execute node – dispatches plan steps to async agents and collects results."""

import asyncio
import logging
import time
from typing import Optional

from services.orchestrator.supervisor.state import (
    ExecutionPlan,
    PlanStep,
    StepResult,
    WorkflowState,
)

logger = logging.getLogger(__name__)


async def _run_agent(
    step: PlanStep,
    context: str = "",
    conversation_history: list[dict[str, str]] | None = None,
) -> StepResult:
    """Run a single async agent for a plan step."""
    from services.agents.registry import get_agent

    t0 = time.perf_counter()
    logger.info("[execute] Agent %s started | step=%s", step.agent_type, step.node_id)
    try:
        agent_fn = get_agent(step.agent_type)
        message = step.message
        if context:
            message = f"Previous context:\n{context}\n\nCurrent task: {message}"

        if step.agent_type == "chat" and conversation_history:
            from services.agents import chat_agent
            result = await chat_agent.run(message, conversation_history=conversation_history)
        else:
            result = await agent_fn(message)
        logger.info("[execute] Agent %s finished | step=%s | %.2fs | result_len=%d",
                     step.agent_type, step.node_id, time.perf_counter() - t0, len(result))
        return StepResult(
            node_id=step.node_id,
            agent_type=step.agent_type,
            result=result,
            success=True,
        )
    except Exception as e:
        logger.exception("[execute] Agent %s FAILED | step=%s | %.2fs: %s",
                         step.agent_type, step.node_id, time.perf_counter() - t0, e)
        return StepResult(
            node_id=step.node_id,
            agent_type=step.agent_type,
            result="",
            error=str(e),
            success=False,
        )


def _get_context(step: PlanStep, results: list[StepResult]) -> str:
    """Build context from dependency results."""
    if not step.dependencies:
        return ""
    result_map = {r.node_id: r.result for r in results if r.success}
    context_parts = []
    for dep_id in step.dependencies:
        if dep_id in result_map:
            context_parts.append(f"[{dep_id}]: {result_map[dep_id]}")
    return "\n\n".join(context_parts)


def _find_ready_steps(
    plan: ExecutionPlan,
    completed_ids: set[str],
    running_ids: set[str],
) -> list[PlanStep]:
    """Find steps whose dependencies are all completed."""
    ready = []
    for step in plan.steps:
        if step.node_id in completed_ids or step.node_id in running_ids:
            continue
        if all(d in completed_ids for d in step.dependencies):
            ready.append(step)
    return ready


async def execute(state: WorkflowState) -> WorkflowState:
    """Execute plan steps asynchronously, with concurrent dispatch for independent steps."""
    t0 = time.perf_counter()
    logger.info("[execute] START | %d total steps", len((state.get("plan") or ExecutionPlan()).steps))
    exec_plan: Optional[ExecutionPlan] = state.get("plan")
    if not exec_plan or not exec_plan.steps:
        return {**state, "error": "No plan to execute"}

    results: list[StepResult] = list(state.get("step_results", []))
    completed_ids = {r.node_id for r in results}
    history = state.get("conversation_history") or []

    while len(completed_ids) < len(exec_plan.steps):
        ready = _find_ready_steps(exec_plan, completed_ids, set())
        if not ready:
            break

        if len(ready) == 1:
            step = ready[0]
            context = _get_context(step, results)
            logger.info("Executing step %s (%s)", step.node_id, step.agent_type)
            result = await _run_agent(step, context, conversation_history=history)
            results.append(result)
            completed_ids.add(step.node_id)
        else:
            logger.info("Executing %d steps in parallel: %s", len(ready), [s.node_id for s in ready])
            tasks = [
                _run_agent(step, _get_context(step, results), conversation_history=history)
                for step in ready
            ]
            batch_results = await asyncio.gather(*tasks)
            for result in batch_results:
                results.append(result)
                completed_ids.add(result.node_id)

    final = results[-1].result if results else ""
    all_results = "\n\n".join(
        f"[{r.node_id}/{r.agent_type}]: {r.result}" for r in results if r.success
    )

    success_count = sum(1 for r in results if r.success)
    logger.info("[execute] DONE  | %d/%d steps succeeded | %.2fs", success_count, len(exec_plan.steps), time.perf_counter() - t0)
    return {
        **state,
        "step_results": results,
        "final_result": final if len(results) == 1 else all_results,
    }
