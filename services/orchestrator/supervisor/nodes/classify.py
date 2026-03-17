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
    needs_clarification = "needs_clarification"


class Classification(BaseModel):
    """Structured classification result from the LLM."""

    intent: Literal["casual", "simple", "complex", "monitor", "needs_clarification"] = Field(
        description=(
            "casual: greetings, small talk, personal/context-dependent questions "
            "(e.g. 'what is my name', 'who am I', 'tell me more', 'what did I say earlier'), "
            "follow-ups referencing previous conversation, short conversational messages. "
            "NEVER use casual for code-related requests: convert to Python, run code, implement algorithm, etc. "
            "simple: single-step factual task requiring one web search or calculation. "
            "Use for code tasks: convert X to Python, run this code, implement algorithm (single step). "
            "Use for scheduling: remind me, run later, schedule X, run daily, run every hour (single step: schedule). "
            "complex: multi-step task needing research, data gathering, analysis, comparison, report generation. "
            "monitor: long-running observation, tracking, or alerting task over a period of time. "
            "needs_clarification: ONLY when the request is truly too vague to execute at all. "
            "Examples: 'research companies' (no industry), 'create a report' (no topic), 'compare them' (no context). "
            "Do NOT use when the user has specified a topic, industry, or scope (e.g. 'petroleum companies', "
            "'business impact of Iran war', 'tech sector') — those are simple or complex."
        )
    )
    next_node: Literal["chat_respond", "ask_user", "plan"] = Field(
        description=(
            "chat_respond: for casual intent – direct conversational response. "
            "ask_user: for needs_clarification – ask user for more details before planning. "
            "plan: for simple, complex, or monitor – create execution plan."
        )
    )
    reasoning: str = Field(description="One-sentence explanation of why this intent was chosen")


CLASSIFY_SYSTEM = (
    "You are an intent classifier for an AI agent platform. "
    "You will receive the user's latest message AND recent conversation history (if any). "
    "Classify the user's LATEST message into exactly one category and decide the next_node.\n\n"
    "next_node rules: casual -> chat_respond; needs_clarification -> ask_user; simple/complex/monitor -> plan.\n\n"
    "Guidelines:\n"
    "- casual: greetings, small talk, follow-up questions that reference the previous conversation "
    "(e.g. 'who was last year', 'tell me more', 'what about X'), short messages that need context.\n"
    "- simple: a factual question or task that requires one web search or calculation. "
    "If the user specified a topic, industry, or scope (e.g. 'petroleum companies', 'Iran war', 'tech sector'), "
    "it is usually simple or complex — NOT needs_clarification.\n"
    "- complex: multi-step task needing research, data gathering, analysis, comparison, report generation.\n"
    "- monitor: long-running observation, tracking, or alerting task over a period of time.\n"
    "- needs_clarification: ONLY when the request is truly too vague to execute. Examples: "
    "'research companies' (no industry), 'create a report' (no topic), 'compare them' (no context), "
    "'find the best one' (no criteria). "
    "Do NOT use needs_clarification when the user has given a specific topic (e.g. 'business impact of Iran war', "
    "'petroleum companies', 'tech sector'). Prefer simple or complex in those cases.\n"
    "If the message contains '[User clarification]', the user already provided clarification — use simple or complex.\n\n"
    "CRITICAL - Scheduling: 'schedule', 'remind', 'run later', 'run tomorrow', 'run daily', 'run every hour' "
    "MUST go to plan (next_node=plan). The scheduler agent handles these. Never route scheduling to chat_respond.\n\n"
    "CRITICAL - Code execution: The casual path has NO tools and cannot run code. "
    "Requests involving code MUST be simple or complex: 'convert X to Python', 'run this code', 'execute', "
    "'implement in Python', 'write a script', 'translate C++ to Python', algorithm implementation, etc. "
    "Use simple when it's a single code task; complex when it needs multiple steps.\n\n"
    "CRITICAL: When in doubt, prefer simple or complex over needs_clarification. "
    "It is better to attempt execution than to ask for more details when the request is reasonably specific."
)

_MAX_HISTORY_FOR_CLASSIFY = 6


async def _classify_with_llm(message: str, history: list[dict[str, str]]) -> tuple[str, str, str]:
    """Classify using structured LLM output with conversation context. Returns (intent, next_node, reasoning)."""
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
    return result.intent, result.next_node, result.reasoning


async def classify(state: WorkflowState) -> WorkflowState:
    """Classify user intent via structured LLM output, using conversation history for context."""
    t0 = time.perf_counter()
    goal = state.get("goal", "")
    history = state.get("conversation_history") or []
    logger.info("[classify] START | goal=%s | history=%d msgs", goal[:120], len(history))

    # User already provided clarification — skip classify, route to plan (agent decision via flag)
    if state.get("is_clarification_resume", False):
        logger.info("[classify] DONE  | is_clarification_resume, routing to plan | %.2fs", time.perf_counter() - t0)
        return {**state, "intent": "complex", "next_node": "plan"}

    from shared.llm import is_llm_available

    if is_llm_available("classify"):
        intent, next_node, reasoning = await _classify_with_llm(goal, history)
        logger.info("[classify] DONE  | intent=%s | next_node=%s | reason=%s | %.2fs",
                    intent, next_node, reasoning[:100], time.perf_counter() - t0)
    else:
        intent = "casual"
        next_node = "chat_respond"
        logger.info("[classify] DONE  | intent=%s | next_node=%s (no LLM, defaulting) | %.2fs",
                    intent, next_node, time.perf_counter() - t0)

    return {**state, "intent": intent, "next_node": next_node}
