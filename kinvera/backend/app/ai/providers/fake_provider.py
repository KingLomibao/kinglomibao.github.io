"""
A scripted, fully deterministic LLM provider used by tests.

Nothing in Kinvera's automated test suite calls a real LLM API - every
AI-layer test (tool-calling loop, grounding, ambiguity handling,
hallucination resistance, the read-only guarantee) runs against this
instead, driven by a fixed script of turns the test itself provides.
"""

from app.ai.providers.base import AssistantTurn, ConversationTurn, LLMProvider, ToolDefinition


class FakeProvider(LLMProvider):
    """Returns each entry in `script`, one per call to `run_turn`, in
    order - regardless of what's actually in `history` or `tools`.

    This is deliberately simple: a test builds the exact sequence of
    `AssistantTurn`s it wants the "model" to produce (e.g. "call this
    tool, then say this final answer") and hands it in as `script`.
    """

    def __init__(self, script: list[AssistantTurn]):
        self._script = list(script)
        self.calls: list[list[ConversationTurn]] = []  # recorded for assertions

    def run_turn(
        self,
        history: list[ConversationTurn],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AssistantTurn:
        self.calls.append(list(history))
        if not self._script:
            raise AssertionError(
                "FakeProvider script exhausted - the orchestrator called run_turn more times than expected."
            )
        return self._script.pop(0)
