"""Centralized LLM factory -- provider-agnostic model instantiation.

Supports OpenAI, Anthropic, Google Gemini, Ollama, and Groq via LangChain's
BaseChatModel interface. Provider selection via environment variables:

    LLM_PROVIDER          global provider  (default: openai)
    LLM_MODEL             global model     (default: gpt-4o-mini)
    LLM_PROVIDER__<CMP>   per-component override  (e.g. LLM_PROVIDER__AGENTS=anthropic)
    LLM_MODEL__<CMP>      per-component override  (e.g. LLM_MODEL__AGENTS=claude-sonnet-4-20250514)

Backward compatible: falls back to OPENAI_API_KEY / OPENAI_MODEL when the new
vars are not set.
"""

import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

_PROVIDER_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "google": "gemini-2.0-flash",
    "ollama": "llama3",
    "groq": "llama-3.3-70b-versatile",
}


def _resolve(component: str | None) -> tuple[str, str]:
    """Resolve (provider, model) for a component, respecting overrides."""
    cmp = (component or "").upper()

    provider = (
        (os.getenv(f"LLM_PROVIDER__{cmp}") if cmp else None)
        or os.getenv("LLM_PROVIDER")
        or "openai"
    )
    model = (
        (os.getenv(f"LLM_MODEL__{cmp}") if cmp else None)
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")  # backward compat
        or _PROVIDER_DEFAULTS.get(provider, "gpt-4o-mini")
    )
    return provider.lower().strip(), model.strip()


def get_llm(
    component: str | None = None,
    temperature: float = 0,
    **kwargs,
) -> BaseChatModel:
    """Return a LangChain chat model for the given component.

    Args:
        component: Logical name (e.g. "agents", "classify", "planner", "evaluator",
                   "chat"). Used for per-component env var overrides.
        temperature: Sampling temperature.
        **kwargs: Extra keyword args forwarded to the provider constructor.

    Returns:
        A BaseChatModel instance.

    Raises:
        ImportError: When the required provider package is not installed.
        ValueError: When the provider name is unrecognized.
    """
    provider, model = _resolve(component)
    logger.debug("[llm] component=%s provider=%s model=%s temperature=%s", component, provider, model, temperature)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY", ""),
            temperature=temperature,
            **kwargs,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            temperature=temperature,
            **kwargs,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            temperature=temperature,
            **kwargs,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
            **kwargs,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            api_key=os.getenv("GROQ_API_KEY", ""),
            temperature=temperature,
            **kwargs,
        )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        f"Supported: openai, anthropic, google, ollama, groq"
    )


def is_llm_available(component: str | None = None) -> bool:
    """Check whether the LLM for a component can be instantiated."""
    provider, _ = _resolve(component)
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if provider == "google":
        return bool(os.getenv("GOOGLE_API_KEY"))
    if provider == "ollama":
        return True  # local, no key needed
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    return False
