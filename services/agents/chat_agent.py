"""Chat agent – casual conversation, no tools needed."""

import logging
import time

from shared.llm import get_llm, is_llm_available

logger = logging.getLogger(__name__)


async def run(message: str, *, conversation_history: list[dict[str, str]] | None = None) -> str:
    """Async chat response via LLM with optional conversation history."""
    t0 = time.perf_counter()
    history_len = len(conversation_history) if conversation_history else 0
    logger.info("[chat] START | msg_len=%d | history=%d msgs", len(message), history_len)

    if not is_llm_available("chat"):
        logger.warning("[chat] No LLM configured")
        return "Hello! I'm the AI assistant. No LLM API key configured."

    llm = get_llm("chat", temperature=0.7)

    if conversation_history:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a friendly AI assistant. Use the conversation history to maintain context."},
        ]
        for msg in conversation_history:
            role = msg.get("role", "user")
            if role in ("user", "assistant", "system"):
                messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})
        response = await llm.ainvoke(messages)
    else:
        response = await llm.ainvoke(message)

    result = (response.content or "").strip() or "Hello! How can I help?"
    logger.info("[chat] DONE | result_len=%d | %.2fs", len(result), time.perf_counter() - t0)
    return result
