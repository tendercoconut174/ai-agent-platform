"""Classify node – determines intent of user message via structured LLM output."""

import logging
import time
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from services.orchestrator.supervisor.state import WorkflowState

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    casual = "casual"
    simple = "simple"
    complex = "complex"
    monitor = "monitor"


class Classification(BaseModel):
    """Structured classification result from the LLM."""

    intent: Literal["casual", "simple", "complex", "monitor"] = Field(
        description=(
            "casual: greetings, small talk, personal/context-dependent questions "
            "(e.g. 'what is my name', 'who am I', 'tell me more', 'what did I say earlier'), "
            "follow-ups referencing previous conversation, short conversational messages. "
            "simple: single-step factual task requiring one tool call (one web search, one calculation, a quick factual answer). "
            "complex: multi-step task needing research, data gathering, analysis, comparison, report generation, or structured output. "
            "monitor: long-running observation, tracking, or alerting task over a period of time."
        )
    )
    reasoning: str = Field(description="One-sentence explanation of why this intent was chosen")


CLASSIFY_SYSTEM = (
    "You are an intent classifier for an AI agent platform. "
    "You will receive the user's latest message AND recent conversation history (if any). "
    "Classify the user's LATEST message into exactly one category.\n\n"
    "Guidelines:\n"
    "- casual: greetings, small talk, follow-up questions that reference the previous conversation "
    "(e.g. 'who was last year', 'tell me more', 'what about X', 'and the previous one?'), "
    "short/vague messages that only make sense with context, personal questions.\n"
    "- simple: a standalone factual question that requires one web search or calculation. "
    "The message must be self-contained -- it should make complete sense without any conversation history.\n"
    "- complex: multi-step task needing research, data gathering, analysis, comparison, report generation, or structured output.\n"
    "- monitor: long-running observation, tracking, or alerting task over a period of time.\n\n"
    "CRITICAL: If the message is short/vague and the conversation history exists, it is almost certainly "
    "a follow-up (casual). A follow-up sent to research would lose all conversation context. "
    "When in doubt, prefer casual."
)

_MAX_HISTORY_FOR_CLASSIFY = 6


async def _classify_with_llm(message: str, history: list[dict[str, str]]) -> tuple[str, str]:
    """Classify using structured LLM output with conversation context. Returns (intent, reasoning)."""
    from shared.llm import get_llm

    llm = get_llm("classify", temperature=0)
    structured_llm = llm.with_structured_output(Classification)

    msgs: list[dict[str, str]] = [{"role": "system", "content": CLASSIFY_SYSTEM}]

    recent = history[-_MAX_HISTORY_FOR_CLASSIFY:] if history else []
    if recent:
        history_text = "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in recent
        )
        msgs.append({
            "role": "user",
            "content": f"=== RECENT CONVERSATION ===\n{history_text}\n=== END ===\n\n"
                       f"Classify this latest message: {message}",
        })
    else:
        msgs.append({"role": "user", "content": message})

    result = await structured_llm.ainvoke(msgs)
    return result.intent, result.reasoning


async def classify(state: WorkflowState) -> WorkflowState:
    """Classify user intent via structured LLM output, using conversation history for context."""
    t0 = time.perf_counter()
    goal = state.get("goal", "")
    history = state.get("conversation_history") or []
    logger.info("[classify] START | goal=%s | history=%d msgs", goal[:120], len(history))

    from shared.llm import is_llm_available

    if is_llm_available("classify"):
        intent, reasoning = await _classify_with_llm(goal, history)
        logger.info("[classify] DONE  | intent=%s | reason=%s | %.2fs", intent, reasoning[:100], time.perf_counter() - t0)
    else:
        intent = "casual"
        logger.info("[classify] DONE  | intent=%s (no LLM, defaulting) | %.2fs", intent, time.perf_counter() - t0)

    return {**state, "intent": intent}
