"""
The tool-calling orchestration loop.

This is the only place that connects "the model asked for a tool" to
"a Kinvera tool actually ran". The loop itself never inspects *what* a
tool returned to make a decision - it just executes whatever the model
asked for (from the fixed, read-only tool registry) and feeds the
result back. All operational reasoning happens either in app/domain/
(before this file ever sees it) or in the model's own explanation
(after this file is done).

Conversation history is kept in memory, per `conversation_id`, for the
lifetime of the running backend process. This is a deliberate Phase 2
scope decision, not an oversight - see docs/ai-architecture.md.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.providers.base import AssistantTurn, ConversationTurn, LLMProvider, ToolDefinition
from app.ai.tools import TOOL_SPECS, execute_tool

MAX_TOOL_ITERATIONS = 5

TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(name=spec.name, description=spec.description, parameters=spec.parameters) for spec in TOOL_SPECS
]


@dataclass
class ToolCallRecord:
    """One entry in the audit trail returned to the API/frontend - the
    tool name and its arguments, never the model's private reasoning."""

    tool: str
    arguments: dict


@dataclass
class ToolResultRecord:
    """The actual structured data a tool returned - this, not the
    model's prose, is what the frontend should treat as ground truth."""

    tool: str
    result: dict


@dataclass
class AssistantChatResult:
    answer: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    tool_results: list[ToolResultRecord] = field(default_factory=list)


class ConversationStore:
    """In-memory conversation history, keyed by conversation_id."""

    def __init__(self) -> None:
        self._conversations: dict[str, list[ConversationTurn]] = {}

    def get(self, conversation_id: str | None) -> list[ConversationTurn]:
        if conversation_id is None:
            return []
        return list(self._conversations.get(conversation_id, []))

    def save(self, conversation_id: str | None, history: list[ConversationTurn]) -> None:
        if conversation_id is not None:
            self._conversations[conversation_id] = history


conversation_store = ConversationStore()


def run_conversation(
    db: Session,
    provider: LLMProvider,
    user_message: str,
    *,
    conversation_id: str | None = None,
) -> AssistantChatResult:
    history = conversation_store.get(conversation_id)
    history.append(ConversationTurn(role="user", text=user_message))

    tool_call_log: list[ToolCallRecord] = []
    tool_result_log: list[ToolResultRecord] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        turn: AssistantTurn = provider.run_turn(history, TOOL_DEFINITIONS, SYSTEM_PROMPT)

        if turn.stop_reason == "tool_use" and turn.tool_calls:
            history.append(ConversationTurn(role="assistant", text=turn.text, tool_calls=turn.tool_calls))

            for call in turn.tool_calls:
                # execute_tool is the single, fixed entry point into the
                # read-only tool registry - there is no other way for a
                # model-requested name to turn into a function call, and
                # no tool in that registry can write to the database.
                result = execute_tool(db, call.name, call.arguments)
                tool_call_log.append(ToolCallRecord(tool=call.name, arguments=call.arguments))
                tool_result_log.append(ToolResultRecord(tool=call.name, result=result))
                history.append(ConversationTurn(role="tool_result", tool_call_id=call.id, tool_output=result))
            continue

        conversation_store.save(conversation_id, history + [ConversationTurn(role="assistant", text=turn.text)])
        return AssistantChatResult(answer=turn.text or "", tool_calls=tool_call_log, tool_results=tool_result_log)

    conversation_store.save(conversation_id, history)
    return AssistantChatResult(
        answer=(
            "I wasn't able to finish answering that within the allowed number of steps. "
            "Please try rephrasing or asking a narrower question."
        ),
        tool_calls=tool_call_log,
        tool_results=tool_result_log,
    )
