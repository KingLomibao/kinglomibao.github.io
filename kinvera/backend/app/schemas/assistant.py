from pydantic import BaseModel, Field

from app.ai.orchestrator import AssistantChatResult


class AssistantChatRequestSchema(BaseModel):
    message: str = Field(..., min_length=1, description="The manager's question, in plain language.")
    conversation_id: str | None = Field(
        default=None, description="Reuse the same id across requests to continue a conversation."
    )


class ToolCallSchema(BaseModel):
    tool: str
    arguments: dict


class ToolResultSchema(BaseModel):
    tool: str
    result: dict


class AssistantChatResponseSchema(BaseModel):
    answer: str
    tool_calls: list[ToolCallSchema] = Field(
        default_factory=list, description="Audit trail of which Kinvera tools were called and with what arguments."
    )
    sources: list[str] = Field(
        default_factory=list, description="Names of the trusted Kinvera capabilities this answer is based on."
    )
    tool_results: list[ToolResultSchema] = Field(
        default_factory=list,
        description=(
            "The raw structured result each tool returned - the source of truth, "
            "independent of the answer text above."
        ),
    )

    @classmethod
    def from_domain(cls, result: AssistantChatResult) -> "AssistantChatResponseSchema":
        return cls(
            answer=result.answer,
            tool_calls=[ToolCallSchema(tool=c.tool, arguments=c.arguments) for c in result.tool_calls],
            sources=sorted({c.tool for c in result.tool_calls}),
            tool_results=[ToolResultSchema(tool=r.tool, result=r.result) for r in result.tool_results],
        )
