"""Intent classifier: casual chat vs complex task."""

import os
import re
import warnings
from typing import Literal

warnings.filterwarnings("ignore", message=".*Pydantic V1.*Python 3.14.*", category=UserWarning)

Intent = Literal["casual", "complex"]

# Heuristic patterns for casual chat
CASUAL_PATTERNS = [
    r"^(hi|hey|hello|howdy|yo)\s*!?$",
    r"^(hi|hey|hello|howdy)\s+there\s*!?$",
    r"^how\s+are\s+you\s*\??$",
    r"^what('s|\s+is)\s+up\s*\??$",
    r"^good\s+(morning|afternoon|evening)\s*!?$",
    r"^(thanks?|thank\s+you)\s*!?$",
    r"^(bye|goodbye|see\s+ya)\s*!?$",
    r"^ok(ay)?\s*!?$",
    r"^yes\s*!?$",
    r"^no\s*!?$",
    r"^sure\s*!?$",
    r"^cool\s*!?$",
    r"^nice\s*!?$",
    r"^lol\s*!?$",
    r"^haha\s*!?$",
    r"^(\?|\.\.\.)\s*$",
]
CASUAL_REGEXES = [re.compile(p, re.IGNORECASE) for p in CASUAL_PATTERNS]

# Keywords that suggest complex task (research, data, tables, etc.)
COMPLEX_KEYWORDS = [
    "research", "summarize", "extract", "compare", "list", "find", "search",
    "tabular", "table", "excel", "pdf", "report", "analyze", "world cup",
    "price", "product", "data", "statistics", "each", "all", "every",
]


def _classify_with_openai(message: str) -> Intent:
    """Use OpenAI to classify intent."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=0,
    )
    prompt = (
        "Is this message casual chat (greeting, small talk, simple question) "
        "or a complex task requiring research/planning/data? Reply ONLY: casual or complex\n"
        f"Message: {message}"
    )
    response = llm.invoke(prompt)
    content = (response.content or "complex").strip().lower()
    return "casual" if "casual" in content else "complex"


def _classify_heuristic(message: str) -> Intent:
    """Rule-based classification when OpenAI not available."""
    msg = message.strip()
    if len(msg) < 3:
        return "casual"
    if any(rx.match(msg) for rx in CASUAL_REGEXES):
        return "casual"
    msg_lower = msg.lower()
    for kw in COMPLEX_KEYWORDS:
        if kw in msg_lower:
            return "complex"
    # Short messages without complex keywords → casual
    if len(msg.split()) <= 5 and "?" not in msg:
        return "casual"
    return "complex"


def classify_intent(message: str) -> Intent:
    """Classify user message as casual chat or complex task.

    Args:
        message: User message.

    Returns:
        'casual' for direct chat, 'complex' for full planning flow.
    """
    if os.getenv("OPENAI_API_KEY"):
        return _classify_with_openai(message)
    return _classify_heuristic(message)
