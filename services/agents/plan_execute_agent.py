"""Plan-and-Execute agent – plans steps upfront, then executes each.

Better for complex, long-horizon tasks than ReAct's iterative approach.
Uses a planner LLM to create steps, then an executor (ReAct) for each step.
"""

import logging
import time
from pydantic import BaseModel, Field

from services.agents.base_agent import create_react_agent
from shared.llm import get_llm, is_llm_available

logger = logging.getLogger(__name__)


class PlanStepSchema(BaseModel):
    """A single step in the plan."""

    step_id: str = Field(description="Unique ID like step_1, step_2")
    instruction: str = Field(description="What to do in this step")
    tool_hint: str = Field(
        default="",
        description="Suggested tool: web_search, execute_python, read_file, write_file, or empty",
    )


class PlanSchema(BaseModel):
    """Structured plan output."""

    steps: list[PlanStepSchema] = Field(description="Ordered list of steps to execute")
    reasoning: str = Field(default="", description="Brief reasoning for the plan")


PLANNER_SYSTEM = """You are a task planner. Break the user's goal into clear, executable steps.
Each step should be a single, focused action that can be done with one or two tool calls.
Available tools: web_search, scrape_url, execute_python, read_file, write_file, list_files, send_email.
Output steps in order. Later steps can use results from earlier steps (mention in instruction).
Keep steps minimal – 1-5 steps usually sufficient."""

# Executor is a ReAct agent – we reuse analysis which has broad tool access
_executor = create_react_agent("analysis", (
    "You are an execution agent. You CAN and MUST run Python code using execute_python when the step requires it. "
    "Never say you cannot run code – you have execute_python and it works. "
    "Execute the given step using available tools: web_search, execute_python, read_file, write_file. "
    "Be concise. Pass through results for the next step."
))


async def run(message: str) -> str:
    """Plan steps, then execute each, passing context forward."""
    t0 = time.perf_counter()
    logger.info("[plan_execute] START | msg_len=%d", len(message))

    if not is_llm_available("planner"):
        logger.warning("[plan_execute] No LLM configured")
        return "[plan_execute] No LLM configured. Use a different agent."

    llm = get_llm("planner", temperature=0)
    structured = llm.with_structured_output(PlanSchema)

    plan: PlanSchema = await structured.ainvoke([
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": message},
    ])

    if not plan.steps:
        logger.warning("[plan_execute] Planner returned no steps")
        return "[plan_execute] Planner returned no steps."

    logger.info("[plan_execute] Plan has %d steps", len(plan.steps))

    context_parts: list[str] = []
    for i, step in enumerate(plan.steps):
        step_msg = f"Step {step.step_id}: {step.instruction}"
        if step.tool_hint:
            step_msg += f" (suggested: {step.tool_hint})"
        if context_parts:
            step_msg = f"Previous results:\n" + "\n\n".join(context_parts) + "\n\n" + step_msg

        logger.info("[plan_execute] Executing step %s/%s", i + 1, len(plan.steps))
        result = await _executor(step_msg)
        context_parts.append(f"[{step.step_id}]: {result}")

    final = context_parts[-1] if context_parts else "[plan_execute] No output."
    logger.info("[plan_execute] DONE | result_len=%d | %.2fs", len(final), time.perf_counter() - t0)
    return final
