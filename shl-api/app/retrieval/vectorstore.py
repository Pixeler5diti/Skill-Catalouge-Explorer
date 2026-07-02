"""
FAISS vector store with disk persistence.
Builds once on first startup, loads on subsequent runs.
"""
from __future__ import annotations
import os
import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Tuple
from app.schemas import AssessmentEntry
from app.utils.logger import logger


class VectorStore:
    INDEX_FILE = "index.faiss"
    IDS_FILE = "ids.json"
    META_FILE = "meta.json"   # stores catalog entry count for consistency check

    def __init__(self, index_dir: str):
        self.index_dir = Path(index_dir)
        self.index: faiss.IndexFlatIP | None = None  # inner-product ≡ cosine for L2-normed
        self.entity_ids: List[str] = []

    def _index_path(self) -> Path:
        return self.index_dir / self.INDEX_FILE

    def _ids_path(self) -> Path:
        return self.index_dir / self.IDS_FILE

    def _meta_path(self) -> Path:
        return self.index_dir / self.META_FILE

    def is_persisted(self) -> bool:
        return (
            self._index_path().exists()
            and self._ids_path().exists()
            and self._meta_path().exists()
        )

    def is_consistent(self, entries: List[AssessmentEntry]) -> bool:
        """Check that the persisted index matches the current catalog."""
        try:
            meta = json.loads(self._meta_path().read_text())
            return meta.get("entry_count") == len(entries)
        except Exception:
            return False

    def build(self, entries: List[AssessmentEntry]) -> None:
        """Build FAISS index from catalog entries and persist to disk."""
        from app.retrieval.embeddings import embed_texts
        logger.info(f"Building FAISS index for {len(entries)} entries…")
        texts = [e.searchable_text for e in entries]
        self.entity_ids = [e.entity_id for e in entries]

        vectors = embed_texts(texts)
        dim = vectors.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(vectors)

        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self._index_path()))
        self._ids_path().write_text(json.dumps(self.entity_ids))
        self._meta_path().write_text(json.dumps({"entry_count": len(entries)}))
        logger.info(f"FAISS index built and saved to {self.index_dir}")

    def load(self) -> None:
        """Load persisted FAISS index from disk."""
        logger.info(f"Loading FAISS index from {self.index_dir}…")
        self.index = faiss.read_index(str(self._index_path()))
        self.entity_ids = json.loads(self._ids_path().read_text())
        logger.info(f"FAISS index loaded ({len(self.entity_ids)} entries)")

    def search(self, query_vector: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        """
        Returns [(entity_id, score)] sorted by descending score.
        score is cosine similarity (0–1 for L2-normed vectors).
        """
        if self.index is None:
            raise RuntimeError("VectorStore not initialised. Call build() or load() first.")
        query_vector = query_vector.reshape(1, -1)
        scores, indices = self.index.search(query_vector, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append((self.entity_ids[idx], float(score)))
        return results
