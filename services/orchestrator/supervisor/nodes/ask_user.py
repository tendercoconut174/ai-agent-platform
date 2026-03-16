"""Ask user node – generates a clarifying question when the goal is ambiguous.

Human-in-the-loop: pauses the workflow and returns a question for the user.
"""

import logging
import time

from pydantic import BaseModel, Field

from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)


class ClarificationOutput(BaseModel):
    """Structured output for the clarifying question."""

    question: str = Field(
        description="A single, clear question to ask the user to get the missing information. "
        "Be specific and helpful. Ask for one thing at a time."
    )
    reasoning: str = Field(description="Brief explanation of what information is missing")


ASK_USER_SYSTEM = (
    "You are an assistant that helps clarify vague or ambiguous user requests. "
    "The user sent a message that cannot be executed without more information. "
    "Generate ONE clear, specific question to ask the user. "
    "The question should be friendly and help the user provide the missing details. "
    "Examples: 'Which industry or sector are you interested in?', "
    "'What topic would you like the report to cover?', "
    "'Could you specify which two items you want me to compare?'"
)


async def ask_user(state: WorkflowState) -> WorkflowState:
    """Generate a clarifying question and pause the workflow (human-in-the-loop)."""
    t0 = time.perf_counter()
    goal = state.get("goal", "")
    logger.info("[ask_user] START | goal=%s", goal[:120])

    from shared.llm import get_llm, is_llm_available

    if is_llm_available("ask_user"):
        llm = get_llm("ask_user", temperature=0.3)
        structured_llm = llm.with_structured_output(ClarificationOutput)
        result = await structured_llm.ainvoke([
            {"role": "system", "content": ASK_USER_SYSTEM},
            {"role": "user", "content": f"User's vague request: {goal}"},
        ])
        question = result.question.strip() or "Could you provide more details about what you're looking for?"
    else:
        question = "Could you provide more details about what you're looking for?"

    logger.info("[ask_user] DONE  | question=%s | %.2fs", question[:80], time.perf_counter() - t0)
    return {
        **state,
        "needs_clarification": True,
        "clarification_question": question,
        "final_result": question,
    }
