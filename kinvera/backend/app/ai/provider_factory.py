"""
Builds the configured LLMProvider from settings.

This is the one place `LLM_API_KEY`/`LLM_MODEL`/`LLM_PROVIDER` get
read - the rest of the AI layer only ever sees the `LLMProvider`
interface, never these settings directly.
"""

from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.base import LLMProvider
from app.core.config import settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when the assistant is asked to run but no LLM_API_KEY
    has been set. This is expected in local/CI environments that
    don't need a live assistant - the rest of Kinvera works fine
    without it."""


def get_llm_provider() -> LLMProvider:
    if not settings.llm_api_key:
        raise LLMNotConfiguredError(
            "No LLM_API_KEY is configured, so the AI assistant is unavailable. "
            "Every other Kinvera feature works normally without it."
        )
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(api_key=settings.llm_api_key, model=settings.llm_model)
    raise ValueError(f"Unsupported LLM_PROVIDER: '{settings.llm_provider}'.")
