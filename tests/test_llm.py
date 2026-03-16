"""Unit tests for LLM factory."""

import os
from unittest.mock import patch

import pytest


class TestIsLlmAvailable:
    """Tests for is_llm_available."""

    def test_openai_available_when_key_set(self) -> None:
        """OpenAI is available when OPENAI_API_KEY is set."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            from shared.llm import is_llm_available

            assert is_llm_available() is True
            assert is_llm_available("agents") is True

    def test_openai_unavailable_when_key_missing(self) -> None:
        """OpenAI is unavailable when OPENAI_API_KEY is not set."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=False):
            from shared.llm import is_llm_available

            # Without key, should be False for openai
            orig = os.environ.get("OPENAI_API_KEY")
            if not orig:
                assert is_llm_available() is False

    def test_ollama_always_available(self) -> None:
        """Ollama is always available (local, no key)."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            from shared.llm import is_llm_available

            assert is_llm_available() is True


class TestGetLlm:
    """Tests for get_llm."""

    def test_returns_openai_when_configured(self) -> None:
        """get_llm returns ChatOpenAI when openai configured."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LLM_PROVIDER": "openai"}, clear=False):
            from shared.llm import get_llm

            llm = get_llm("agents")
            assert llm is not None
            assert "openai" in type(llm).__module__.lower() or "OpenAI" in type(llm).__name__

    def test_raises_for_unknown_provider(self) -> None:
        """get_llm raises ValueError for unknown provider."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown_provider"}, clear=False):
            from shared.llm import get_llm

            with pytest.raises(ValueError, match="Unknown"):
                get_llm()
