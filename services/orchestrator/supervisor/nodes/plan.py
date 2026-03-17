"""Plan node – creates an execution plan via structured LLM output."""

import logging
import time
from typing import Literal

from pydantic import BaseModel, Field

from services.orchestrator.supervisor.state import ExecutionPlan, PlanStep, WorkflowState

logger = logging.getLogger(__name__)


class PlanStepSchema(BaseModel):
    """Schema for a single step the LLM returns."""

    node_id: str = Field(description="Unique step ID like step_1, step_2")
    agent_type: Literal["research", "analysis", "generator", "code", "monitor", "chat", "plan_execute", "scheduler"] = Field(
        description=(
            "research: web search, data gathering from the internet. "
            "analysis: summarize, compare, extract patterns from data. "
            "generator: create reports, documents, structured output. "
            "code: run calculations, data processing, number crunching. "
            "monitor: long-running observation (only for monitoring tasks). "
            "chat: casual conversation. "
            "plan_execute: complex multi-step tasks – plans upfront then executes (use for research+analysis+format). "
            "scheduler: schedule tasks for future execution (remind, run later, daily, hourly, weekly, every X minutes)."
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
    "Available agent types and their capabilities:\n"
    "- research: web search, data gathering from the internet (tools: web_search, scrape_url)\n"
    "- analysis: summarize, compare, extract patterns (tools: web_search, execute_python, read_file)\n"
    "- generator: create reports, documents, structured output, SEND EMAIL (tools: web_search, write_file, read_file, execute_python, send_email)\n"
    "- code: write and execute Python code for calculations/data processing (tools: execute_python, read_file, write_file)\n"
    "- monitor: web search and scrape for tracking tasks – ONE-TIME observation (tools: web_search, scrape_url). "
    "Do NOT use monitor for 'every X seconds/minutes' or 'talk to me every...' – those use scheduler.\n"
    "- chat: casual conversation (no tools)\n"
    "- plan_execute: for complex tasks needing research+analysis+format – plans steps then executes each\n"
    "- scheduler: schedule tasks for future execution (remind, run later, daily, hourly, weekly, every X minutes).\n\n"
    "Platform LIMITATIONS (capabilities NOT available):\n"
    "- NO file upload to external services -- cannot post to social media, upload to cloud storage, etc.\n"
    "- NO database access -- cannot query or write to external databases\n"
    "- NO browser interaction -- cannot fill forms, click buttons, or log into websites\n"
    "- Code execution is sandboxed -- only standard library modules (math, json, re, datetime, collections, etc.)\n\n"
    "Rules:\n"
    "- Use the fewest steps necessary. A single-step plan is fine for simple goals.\n"
    "- Set dependencies correctly: a step that needs results from step_1 should list ['step_1'] in dependencies.\n"
    "- Steps with no dependencies can run in parallel.\n"
    "- If the user asks to schedule, remind, run later, run daily, run every hour, run every X minutes, "
    "'talk to me every...', 'notify me every...', use scheduler as the first (and usually only) step. "
    "Never use monitor for recurring tasks – monitor runs once and stops.\n"
    "- If the user asks for something the platform CANNOT do (e.g. upload to cloud, run for 1 hour), "
    "plan only the parts that ARE possible and include a note about unsupported parts.\n"
    "- Each step should complete in under 60 seconds. Break large tasks into smaller pieces.\n"
    "- Do NOT use 'chat' for tasks that need tools or research.\n"
    "- When conversation context is provided, the goal may be a follow-up (e.g. 'can you write one with python'). "
    "Use the context to resolve references like 'one', 'it', 'that' — and make step messages explicit "
    "(e.g. 'Write a Python calculator app' not 'Write a Python script based on the user request')."
)


def _format_conversation_for_plan(history: list[dict[str, str]], max_chars: int = 1500) -> str:
    """Format conversation history for planner context. Truncates long assistant responses."""
    if not history:
        return ""
    lines = []
    total = 0
    for msg in history[-6:]:  # Last 6 messages (3 exchanges)
        role = msg.get("role", "user")
        content = (msg.get("content") or "")[:800]
        if total + len(content) > max_chars:
            content = content[: max_chars - total - 20] + "..."
        lines.append(f"{role.upper()}: {content}")
        total += len(content)
        if total >= max_chars:
            break
    return "\n".join(lines)


async def _plan_with_llm(
    goal: str,
    output_format: str = "json",
    format_hint: str = "",
    iteration: int = 0,
    previous_feedback: str = "",
    conversation_history: list[dict[str, str]] | None = None,
) -> ExecutionPlan:
    from shared.llm import get_llm

    llm = get_llm("planner", temperature=0)
    structured_llm = llm.with_structured_output(PlanOutput)

    format_hint = ""  # Set from state (agent-inferred via preference_inference)
    user_msg = goal
    if conversation_history:
        ctx = _format_conversation_for_plan(conversation_history)
        if ctx:
            user_msg = (
                f"=== CONVERSATION CONTEXT (resolve 'one', 'it', 'that' from this) ===\n{ctx}\n"
                f"=== CURRENT GOAL ===\n{goal}"
            )
    if format_hint:
        user_msg += f"\n\nOutput format instruction: {format_hint}"

    if iteration > 0 and previous_feedback:
        user_msg += (
            f"\n\nIMPORTANT: This is attempt #{iteration + 1}. "
            f"The previous plan failed:\n{previous_feedback}\n"
            f"Create a DIFFERENT plan that avoids the same issues. "
            f"Use different step IDs (e.g. step_{iteration}a, step_{iteration}b)."
        )

    result: PlanOutput = await structured_llm.ainvoke([
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": user_msg},
    ])

    prefix = f"i{iteration}_" if iteration > 0 else ""
    steps = [
        PlanStep(
            node_id=f"{prefix}{s.node_id}",
            agent_type=s.agent_type,
            message=s.message,
            dependencies=[f"{prefix}{d}" for d in s.dependencies],
        )
        for s in result.steps
    ]

    if format_hint and steps:
        steps[-1].message += f" {format_hint}"

    return ExecutionPlan(steps=steps, reasoning=result.reasoning)


def _build_previous_feedback(state: WorkflowState) -> str:
    """Summarize previous step results for the planner to learn from failures."""
    prev_results = state.get("step_results") or []
    if not prev_results:
        return ""
    lines = []
    for r in prev_results:
        status = "OK" if r.success else f"FAILED: {r.error or 'unknown'}"
        snippet = (r.result or "")[:200]
        lines.append(f"- {r.node_id} ({r.agent_type}): {status} | output: {snippet}")
    return "\n".join(lines)


async def plan(state: WorkflowState) -> WorkflowState:
    """Create an execution plan for the goal via structured LLM output."""
    t0 = time.perf_counter()
    goal = state.get("goal", "")
    output_format = state.get("output_format", "json")
    format_hint = state.get("format_hint", "")
    iteration = state.get("iteration_count", 0)
    logger.info("[plan] START | iteration=%d | format=%s | goal=%s", iteration, output_format, goal[:120])

    from shared.llm import is_llm_available

    previous_feedback = _build_previous_feedback(state) if iteration > 0 else ""
    conversation_history = state.get("conversation_history") or []

    if is_llm_available("planner"):
        execution_plan = await _plan_with_llm(
            goal, output_format, format_hint, iteration, previous_feedback, conversation_history
        )
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
        "step_results": [],
        "current_step_index": 0,
    }
