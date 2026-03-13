"""Chat agent – casual conversation, no tools needed."""

from shared.llm import get_llm, is_llm_available


async def run(message: str, *, conversation_history: list[dict[str, str]] | None = None) -> str:
    """Async chat response via LLM with optional conversation history."""
    if not is_llm_available("chat"):
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

    return (response.content or "").strip() or "Hello! How can I help?"
