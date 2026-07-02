"""Central configuration. All tunables live here."""
from pathlib import Path
from pydantic_settings import BaseSettings

# Workspace root (two levels up from this file: shl-api/app/ -> shl-api/ -> /)
_WORKSPACE_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # ── Groq ──────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_intent_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 1024
    groq_intent_max_tokens: int = 10  # classification only

    # ── Embedding ─────────────────────────────────────────────────────────
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # ── Catalog ───────────────────────────────────────────────────────────
    catalog_path: str = str(
        _WORKSPACE_ROOT
        / "attached_assets"
        / "Pasted--entity-id-4302-name-Global-Skills-Development-Report-l_1782925068934.txt"
    )

    # ── FAISS index persistence ────────────────────────────────────────────
    faiss_index_dir: str = str(Path(__file__).parent.parent / "data" / "faiss_index")

    # ── Retrieval ─────────────────────────────────────────────────────────
    top_k_retrieve: int = 20   # candidates from hybrid search
    top_k_return: int = 10     # max returned to LLM / user
    bm25_weight: float = 0.3   # hybrid weight for BM25
    semantic_weight: float = 0.7  # hybrid weight for semantic

    model_config = {
        # Check .env in shl-api/ first, then fall back to the project root .env
        "env_file": [".env", "../.env"],
        "extra": "ignore",
    }


settings = Settings()
