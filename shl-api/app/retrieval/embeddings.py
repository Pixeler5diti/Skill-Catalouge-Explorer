"""Embedding model wrapper using sentence-transformers."""
from __future__ import annotations
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.utils.logger import logger

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.embed_model}")
        _model = SentenceTransformer(settings.embed_model)
        logger.info("Embedding model loaded.")
    return _model


def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """
    Encode a list of strings to L2-normalised float32 vectors.
    BGE models perform best with L2 normalisation for cosine similarity.
    """
    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # L2 normalise → dot product == cosine
        convert_to_numpy=True,
    )
    return vectors.astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    """Encode a single query string."""
    # BGE recommends a query instruction prefix for retrieval
    prefixed = f"Represent this sentence for searching relevant passages: {text}"
    return embed_texts([prefixed])[0]
