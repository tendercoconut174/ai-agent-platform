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
from shared.code_approval_context import (
    CodeApprovalContext,
    CodeApprovalRequired,
    clear_code_approval_context,
    set_code_approval_context,
)

logger = logging.getLogger(__name__)

CODE_AGENT_TYPES = {"code", "analysis", "generator"}


async def _run_agent(
    step: PlanStep,
    context: str = "",
    conversation_history: list[dict[str, str]] | None = None,
    code_approval_ctx: Optional[CodeApprovalContext] = None,
) -> StepResult:
    """Run a single async agent for a plan step."""
    from services.agents.registry import get_agent

    t0 = time.perf_counter()
    logger.info("[execute] Agent %s started | step=%s", step.agent_type, step.node_id)
    try:
        set_code_approval_context(code_approval_ctx)
        agent_fn = get_agent(step.agent_type)
        message = step.message
        if context:
            message = f"Previous context:\n{context}\n\nCurrent task: {message}"
        # Inject conversation history for follow-up context (all agents except chat)
        if conversation_history and step.agent_type != "chat":
            conv_ctx = _format_conversation_for_agent(conversation_history)
            if conv_ctx:
                message = (
                    f"=== CONVERSATION CONTEXT (user's follow-up; resolve 'one', 'it', 'that') ===\n"
                    f"{conv_ctx}\n\n=== TASK ===\n{message}"
                )

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
    except CodeApprovalRequired as e:
        clear_code_approval_context()
        raise e
    except Exception as e:
        clear_code_approval_context()
        logger.exception("[execute] Agent %s FAILED | step=%s | %.2fs: %s",
                         step.agent_type, step.node_id, time.perf_counter() - t0, e)
        return StepResult(
            node_id=step.node_id,
            agent_type=step.agent_type,
            result="",
            error=str(e),
            success=False,
        )
    finally:
        clear_code_approval_context()


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


def _format_conversation_for_agent(history: list[dict[str, str]], max_chars: int = 1200) -> str:
    """Format conversation history for agent context. Truncates long responses."""
    if not history:
        return ""
    lines = []
    total = 0
    for msg in history[-6:]:
        role = msg.get("role", "user")
        content = (msg.get("content") or "")[:600]
        if total + len(content) > max_chars:
            content = content[: max_chars - total - 20] + "..."
        lines.append(f"{role.upper()}: {content}")
        total += len(content)
        if total >= max_chars:
            break
    return "\n".join(lines)


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
    deadline = state.get("deadline", float("inf"))
    require_approval = state.get("require_code_approval", False)
    workflow_id = state.get("workflow_id", "")
    session_id = state.get("session_id")
    goal = state.get("goal", "")

    while len(completed_ids) < len(exec_plan.steps):
        remaining = deadline - time.perf_counter()
        if remaining < 20:
            logger.warning("[execute] deadline approaching (%.1fs left), stopping early", remaining)
            break

        ready = _find_ready_steps(exec_plan, completed_ids, set())
        if not ready:
            break

        progress_queue = state.get("progress_queue")

        if len(ready) == 1:
            step = ready[0]
            context = _get_context(step, results)
            logger.info("Executing step %s (%s)", step.node_id, step.agent_type)
            code_approval_ctx = None
            if require_approval and step.agent_type in CODE_AGENT_TYPES:
                code_approval_ctx = CodeApprovalContext(
                    workflow_id=workflow_id,
                    step_id=step.node_id,
                    session_id=session_id,
                )
            if progress_queue:
                await progress_queue.put({"type": "step_start", "node_id": step.node_id, "agent_type": step.agent_type})
            try:
                result = await _run_agent(step, context, conversation_history=history, code_approval_ctx=code_approval_ctx)
            except CodeApprovalRequired as e:
                from shared.pending_code_approval_manager import save_pending_code_approval
                approval_id = save_pending_code_approval(
                    workflow_id=e.workflow_id,
                    session_id=e.session_id,
                    code=e.code,
                    step_id=e.step_id,
                    original_goal=goal,
                    output_format=state.get("output_format", "json"),
                )
                return {
                    **state,
                    "needs_code_approval": True,
                    "pending_code_approval_id": approval_id,
                    "pending_step_id": e.step_id,
                    "code_to_approve": e.code,
                    "step_results": results,
                }
            results.append(result)
            completed_ids.add(step.node_id)
            if progress_queue:
                await progress_queue.put({
                    "type": "step_done",
                    "node_id": result.node_id,
                    "agent_type": result.agent_type,
                    "result": (result.result or "")[:500],
                    "error": result.error,
                    "success": result.success,
                })
        else:
            logger.info("Executing %d steps in parallel: %s", len(ready), [s.node_id for s in ready])
            for s in ready:
                if progress_queue:
                    await progress_queue.put({"type": "step_start", "node_id": s.node_id, "agent_type": s.agent_type})
            code_approval_ctx = None
            if require_approval and len(ready) == 1 and ready[0].agent_type in CODE_AGENT_TYPES:
                step = ready[0]
                code_approval_ctx = CodeApprovalContext(
                    workflow_id=workflow_id,
                    step_id=step.node_id,
                    session_id=session_id,
                )
            tasks = [
                _run_agent(step, _get_context(step, results), conversation_history=history, code_approval_ctx=code_approval_ctx if step.agent_type in CODE_AGENT_TYPES else None)
                for step in ready
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, br in enumerate(batch_results):
                if isinstance(br, CodeApprovalRequired):
                    from shared.pending_code_approval_manager import save_pending_code_approval
                    approval_id = save_pending_code_approval(
                        workflow_id=br.workflow_id,
                        session_id=br.session_id,
                        code=br.code,
                        step_id=br.step_id,
                        original_goal=goal,
                        output_format=state.get("output_format", "json"),
                    )
                    return {
                        **state,
                        "needs_code_approval": True,
                        "pending_code_approval_id": approval_id,
                        "pending_step_id": br.step_id,
                        "code_to_approve": br.code,
                        "step_results": results,
                    }
            resolved_results = [
                r if isinstance(r, StepResult) else StepResult(node_id=ready[i].node_id, agent_type=ready[i].agent_type, result="", error=str(r), success=False)
                for i, r in enumerate(batch_results)
            ]
            for result in resolved_results:
                results.append(result)
                completed_ids.add(result.node_id)
                if progress_queue:
                    await progress_queue.put({
                        "type": "step_done",
                        "node_id": result.node_id,
                        "agent_type": result.agent_type,
                        "result": (result.result or "")[:500],
                        "error": result.error,
                        "success": result.success,
                    })

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
