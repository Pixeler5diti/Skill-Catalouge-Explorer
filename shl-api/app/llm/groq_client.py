"""Groq LLM client with retry and error handling."""
from __future__ import annotations
import time
from typing import List, Dict, Optional
from groq import Groq, APIError, RateLimitError
from app.config import settings
from app.utils.logger import logger

_client: Optional[Groq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to the environment or .env file."
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.1,
    json_mode: bool = False,
    retries: int = 2,
) -> str:
    """
    Call Groq chat completion with automatic retry on rate-limit errors.
    Returns the assistant message content as a string.
    """
    client = get_client()
    model = model or settings.groq_model
    max_tokens = max_tokens or settings.groq_max_tokens
    kwargs: Dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(retries + 1):
        try:
            t0 = time.perf_counter()
            response = client.chat.completions.create(**kwargs)
            latency_ms = round((time.perf_counter() - t0) * 1000)
            content = response.choices[0].message.content or ""
            usage = response.usage
            logger.info(
                "Groq call complete",
                extra={
                    "latency_ms": latency_ms,
                    "tokens": usage.total_tokens if usage else "?",
                },
            )
            return content
        except (RateLimitError, APIError) as e:
            # Retry on rate-limit and transient server errors (5xx)
            is_transient = isinstance(e, RateLimitError) or (
                isinstance(e, APIError) and getattr(e, "status_code", 0) >= 500
            )
            if is_transient and attempt < retries:
                wait = 2 ** attempt
                logger.info(f"Transient error ({type(e).__name__}). Retrying in {wait}s…")
                time.sleep(wait)
            else:
                logger.error(f"Groq API error: {e}", extra={"error": str(e)})
                raise
