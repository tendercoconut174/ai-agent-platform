"""Plan node – creates an execution plan via structured LLM output."""

import logging
import time
from typing import Literal

from pydantic import BaseModel, Field

from services.orchestrator.supervisor.state import ExecutionPlan, PlanStep, WorkflowState

logger = logging.getLogger(__name__)

FORMAT_HINTS = {
    "xl": "Format the final output as a markdown table with | separators.",
    "pdf": "Format the final output with clear headings, structured lists, and readable paragraphs.",
    "audio": "Format the final output as a concise spoken summary.",
    "json": "",
}


class PlanStepSchema(BaseModel):
    """Schema for a single step the LLM returns."""

    node_id: str = Field(description="Unique step ID like step_1, step_2")
    agent_type: Literal["research", "analysis", "generator", "code", "monitor", "chat"] = Field(
        description=(
            "research: web search, data gathering from the internet. "
            "analysis: summarize, compare, extract patterns from data. "
            "generator: create reports, documents, structured output. "
            "code: run calculations, data processing, number crunching. "
            "monitor: long-running observation (only for monitoring tasks). "
            "chat: casual conversation."
        )
    )
    message: str = Field(description="What this step should do -- a clear instruction for the agent")
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of node_ids this step depends on (empty if no dependencies)",
    )


class PlanOutput(BaseModel):
    """Structured plan output from the LLM."""

    steps: list[PlanStepSchema] = Field(description="Ordered list of execution steps")
    reasoning: str = Field(description="Brief explanation of why this plan was chosen")


PLAN_SYSTEM = (
    "You are a task planner for an AI agent platform. "
    "Break down the user's goal into execution steps. Each step is handled by a specialized agent.\n\n"
    "Rules:\n"
    "- Use the fewest steps necessary. A single-step plan is fine for simple goals.\n"
    "- Set dependencies correctly: a step that needs results from step_1 should list ['step_1'] in dependencies.\n"
    "- Steps with no dependencies can run in parallel.\n"
    "- Use 'research' for anything requiring web search or data gathering.\n"
    "- Use 'generator' for the final step when structured output (tables, reports) is needed.\n"
    "- Do NOT use 'chat' for tasks that need tools or research."
)


async def _plan_with_llm(goal: str, output_format: str = "json") -> ExecutionPlan:
    from shared.llm import get_llm

    llm = get_llm("planner", temperature=0)
    structured_llm = llm.with_structured_output(PlanOutput)

    format_hint = FORMAT_HINTS.get(output_format, "")
    user_msg = goal
    if format_hint:
        user_msg += f"\n\nOutput format instruction: {format_hint}"

    result: PlanOutput = await structured_llm.ainvoke([
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": user_msg},
    ])

    steps = [
        PlanStep(
            node_id=s.node_id,
            agent_type=s.agent_type,
            message=s.message,
            dependencies=s.dependencies,
        )
        for s in result.steps
    ]

    if format_hint and steps:
        steps[-1].message += f" {format_hint}"

    return ExecutionPlan(steps=steps, reasoning=result.reasoning)


async def plan(state: WorkflowState) -> WorkflowState:
    """Create an execution plan for the goal via structured LLM output."""
    t0 = time.perf_counter()
    goal = state.get("goal", "")
    output_format = state.get("output_format", "json")
    iteration = state.get("iteration_count", 0)
    logger.info("[plan] START | iteration=%d | format=%s | goal=%s", iteration, output_format, goal[:120])

    from shared.llm import is_llm_available

    if is_llm_available("planner"):
        execution_plan = await _plan_with_llm(goal, output_format)
    else:
        execution_plan = ExecutionPlan(
            steps=[PlanStep(node_id="step_1", agent_type="research", message=goal)],
            reasoning="No LLM available, default single research step",
        )

    step_summary = ", ".join(f"{s.node_id}({s.agent_type})" for s in execution_plan.steps)
    logger.info("[plan] DONE  | %d steps=[%s] | reasoning=%s | %.2fs",
                len(execution_plan.steps), step_summary, execution_plan.reasoning[:80], time.perf_counter() - t0)
    return {
        **state,
        "plan": execution_plan,
        "step_results": state.get("step_results", []),
        "current_step_index": 0,
    }
