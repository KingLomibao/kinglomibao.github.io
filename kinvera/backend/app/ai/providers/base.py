"""
The LLM provider abstraction.

Nothing outside this `providers/` package talks to a specific LLM
vendor's SDK or wire format. The tool layer, the orchestrator, and the
API route all work in terms of the plain dataclasses defined here.
That's what lets Kinvera switch models (or add a second provider
later) without touching the business logic, the tools, or the API
contract - only a new file in this package.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolCall:
    """One request from the model to run a specific tool."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ConversationTurn:
    """One entry in the conversation, in Kinvera's own neutral shape.

    - role="user": a message from the manager.
    - role="assistant": a reply from the model - free text, one or
      more tool calls, or both.
    - role="tool_result": the Kinvera tool layer reporting back what a
      previously-requested tool call actually returned.
    """

    role: Literal["user", "assistant", "tool_result"]
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    tool_output: dict[str, Any] | None = None


@dataclass
class AssistantTurn:
    """What a provider hands back for one turn: some text, and/or a
    request to call one or more tools."""

    text: str | None
    tool_calls: list[ToolCall]
    stop_reason: Literal["tool_use", "end_turn"]


@dataclass
class ToolDefinition:
    """Vendor-neutral description of one callable tool, translated by
    each provider into that vendor's own tool-definition format."""

    name: str
    description: str
    parameters: dict[str, Any]


class LLMProvider(ABC):
    """A chat-completion backend that supports tool calling.

    `system_prompt` and `tools` are passed on every call rather than
    fixed at construction time so the same provider instance can be
    reused across requests (and, in tests, across scripted turns)
    without carrying request-specific state.
    """

    @abstractmethod
    def run_turn(
        self,
        history: list[ConversationTurn],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AssistantTurn:
        """Given the conversation so far, produce the model's next turn."""
