"""Direct chat: simple LLM response for casual conversation (no planning/queue)."""

import os
import warnings
from typing import Optional

warnings.filterwarnings("ignore", message=".*Pydantic V1.*Python 3.14.*", category=UserWarning)


def _chat_with_openai(message: str) -> str:
    """Use OpenAI for direct chat response."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=0.7,
    )
    response = llm.invoke(message)
    return (response.content or "").strip() or "I'm here to help. How can I assist you?"


def _chat_fallback(message: str) -> str:
    """Fallback when OpenAI not configured."""
    return "Hello! I'm the AI assistant. Set OPENAI_API_KEY for full chat. How can I help?"


def direct_chat(message: str) -> str:
    """Return a direct chat response without planning or workers.

    Args:
        message: User message.

    Returns:
        Chat response string.
    """
    if os.getenv("OPENAI_API_KEY"):
        return _chat_with_openai(message)
    return _chat_fallback(message)
