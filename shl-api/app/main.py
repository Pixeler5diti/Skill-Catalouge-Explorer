"""
FastAPI application entry point.
Initialises catalog, embeddings, and FAISS index at startup.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.catalog.loader import load_catalog
from app.catalog.preprocess import preprocess_catalog
from app.retrieval.vectorstore import VectorStore
from app.retrieval.retriever import ConstraintAwareRetriever
from app.conversation.chat_engine import ChatEngine
from app.utils.logger import logger

# Global engine instance (set during lifespan startup)
engine: ChatEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    logger.info("SHL Recommender starting up…")

    # 1. Load catalog
    raw_entries = load_catalog(settings.catalog_path)

    # 2. Preprocess
    entries, by_id, by_name = preprocess_catalog(raw_entries)

    # 3. Build / load FAISS index (with catalog consistency check)
    vector_store = VectorStore(settings.faiss_index_dir)
    if vector_store.is_persisted() and vector_store.is_consistent(entries):
        vector_store.load()
    else:
        if vector_store.is_persisted():
            logger.info("Catalog changed since last index build — rebuilding…")
        else:
            logger.info("No persisted index found — building from scratch (one-time, ~1 min)…")
        vector_store.build(entries)

    # 4. Build constraint-aware retriever
    retriever = ConstraintAwareRetriever(entries, vector_store)

    # 5. Instantiate chat engine
    engine = ChatEngine(retriever, by_id, by_name)
    logger.info(f"Ready. Catalog size: {len(entries)} assessments.")

    yield

    logger.info("SHL Recommender shutting down.")
    engine = None


app = FastAPI(
    title="SHL Assessment Recommender",
    version="1.0.0",
    description="Conversational retrieval system for SHL catalog recommendations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import router  # noqa: E402 — must be after app creation
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
