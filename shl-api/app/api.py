"""API route definitions."""
from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ChatResponse
from app.utils.logger import logger

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Stateless conversational assessment recommender.
    All conversation history must be passed in messages[].
    """
    from app.main import engine  # imported here to avoid circular deps at startup

    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Catalog index is still initialising. Please retry in a moment.",
        )

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages[] must not be empty.")

    # Validate roles — reject system role to block prompt-injection via message history
    for msg in request.messages:
        if msg.role not in ("user", "assistant"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid message role: {msg.role!r}. Only 'user' and 'assistant' are accepted.",
            )

    try:
        return engine.process(request.messages)
    except Exception as e:
        logger.error(f"Chat processing error: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal error processing request.")
