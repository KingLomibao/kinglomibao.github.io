from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.orchestrator import run_conversation
from app.ai.provider_factory import LLMNotConfiguredError, get_llm_provider
from app.ai.providers.base import LLMProvider
from app.database import get_db
from app.schemas.assistant import AssistantChatRequestSchema, AssistantChatResponseSchema

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def require_llm_provider() -> LLMProvider:
    """Wraps get_llm_provider so an unconfigured assistant returns a
    clean 503 instead of an unhandled 500 from the dependency."""
    try:
        return get_llm_provider()
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chat", response_model=AssistantChatResponseSchema)
def chat(
    request: AssistantChatRequestSchema,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(require_llm_provider),
) -> AssistantChatResponseSchema:
    """Ask the Kinvera assistant a workforce question.

    The assistant explains results computed by Kinvera's existing,
    deterministic domain logic - it never decides eligibility,
    staffing, or simulation outcomes itself. See docs/ai-architecture.md.
    """
    result = run_conversation(db, provider, request.message, conversation_id=request.conversation_id)
    return AssistantChatResponseSchema.from_domain(result)


@router.get("/health", tags=["health"])
def assistant_health() -> dict[str, bool]:
    """Whether the assistant is configured (an LLM_API_KEY is set) -
    not whether the LLM provider is currently reachable."""
    try:
        get_llm_provider()
        return {"configured": True}
    except LLMNotConfiguredError:
        return {"configured": False}
