"""
Real LLM provider backed by the Anthropic Messages API.

This is the only file in Kinvera that imports the `anthropic` package
or knows anything about its wire format - everything else in the AI
layer works through the neutral types in `base.py`.
"""

import json

import anthropic

from app.ai.providers.base import AssistantTurn, ConversationTurn, LLMProvider, ToolCall, ToolDefinition


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def run_turn(
        self,
        history: list[ConversationTurn],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AssistantTurn:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=_to_anthropic_messages(history),
            tools=[_to_anthropic_tool(t) for t in tools],
        )

        text_parts = [block.text for block in response.content if block.type == "text"]
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]

        return AssistantTurn(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
        )


def _to_anthropic_tool(tool: ToolDefinition) -> dict:
    return {"name": tool.name, "description": tool.description, "input_schema": tool.parameters}


def _to_anthropic_messages(history: list[ConversationTurn]) -> list[dict]:
    """Translate Kinvera's neutral conversation history into Anthropic's
    message format. Anthropic requires every tool_result produced in
    response to one assistant turn to arrive together in a single,
    immediately-following user message - so consecutive `tool_result`
    turns here are batched into one message.
    """
    messages: list[dict] = []
    i = 0
    while i < len(history):
        turn = history[i]

        if turn.role == "user":
            messages.append({"role": "user", "content": turn.text or ""})
            i += 1

        elif turn.role == "assistant":
            content: list[dict] = []
            if turn.text:
                content.append({"type": "text", "text": turn.text})
            for call in turn.tool_calls:
                content.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
            messages.append({"role": "assistant", "content": content})
            i += 1

        elif turn.role == "tool_result":
            batch = []
            while i < len(history) and history[i].role == "tool_result":
                batch.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": history[i].tool_call_id,
                        "content": json.dumps(history[i].tool_output),
                    }
                )
                i += 1
            messages.append({"role": "user", "content": batch})

        else:  # pragma: no cover - exhaustive over the Literal above
            raise ValueError(f"Unknown conversation turn role: {turn.role}")

    return messages
