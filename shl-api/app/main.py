"""
FastAPI application entry point.
Temporary debug version to isolate Render startup issues.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.catalog.loader import load_catalog
from app.catalog.preprocess import preprocess_catalog
from app.retrieval.vectorstore import VectorStore
from app.utils.logger import logger

# Global engine (still disabled)
engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine

    logger.info("SHL Recommender starting up...")

    # 1. Load catalog
    raw_entries = load_catalog(settings.catalog_path)

    # 2. Preprocess catalog
    entries, by_id, by_name = preprocess_catalog(raw_entries)

    logger.info(f"Catalog loaded successfully ({len(entries)} assessments).")

    # 3. Load persisted FAISS index
    vector_store = VectorStore(settings.faiss_index_dir)

    if not vector_store.is_persisted():
        raise RuntimeError(
            "Persisted FAISS index not found. Build it locally and commit "
            "shl-api/data/faiss_index/index.faiss."
        )

    logger.info("Loading persisted FAISS index...")
    vector_store.load()
    logger.info("FAISS index loaded successfully.")

    # 4. Create retriever
    logger.info("Initializing retriever...")
    from app.retrieval.retriever import ConstraintAwareRetriever

    retriever = ConstraintAwareRetriever(entries, vector_store)
    logger.info("Retriever initialized.")

    # 5. Create chat engine
    logger.info("Initializing ChatEngine...")
    from app.conversation.chat_engine import ChatEngine

    engine = ChatEngine(retriever, by_id, by_name)
    logger.info("ChatEngine initialized.")

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
    allow_origins=[
        "https://skill-catalouge-explorer-1.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://skill-catalouge-explorer-1.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
from app.api import router

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )