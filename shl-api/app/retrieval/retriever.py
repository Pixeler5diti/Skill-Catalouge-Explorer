"""
Constraint-aware hybrid retriever.

Scoring formula:
  FinalScore = metadata_score + BM25_normalised * W_BM25 + embedding_normalised * W_EMBED

Metadata weights (absolute additive points — dominate over signal weights):
  language exact match   +5
  domain exact match     +5
  role keyword           +4
  compliance topic       +4
  assessment type        +3
  job level              +1

Signal weights (BM25 and embedding provide recall, not precision):
  BM25 normalised        * 2  (max 2 pts)
  embedding normalised   * 1  (max 1 pt)
"""
from __future__ import annotations

import numpy as np
from typing import List, Dict, Tuple, Any

from rank_bm25 import BM25Okapi

from app.schemas import AssessmentEntry
from app.retrieval.vectorstore import VectorStore
from app.retrieval.embeddings import embed_query
from app.config import settings
from app.utils.logger import logger

# ── Metadata point values ─────────────────────────────────────────────────────
_W_LANGUAGE   = 5.0
_W_DOMAIN     = 5.0
_W_ROLE       = 4.0
_W_COMPLIANCE = 4.0
_W_TEST_TYPE  = 3.0
_W_JOB_LEVEL  = 1.0

# ── Recall signal weights ─────────────────────────────────────────────────────
_W_BM25  = 2.0   # normalised BM25 score coefficient
_W_EMBED = 1.0   # normalised embedding score coefficient

# ── Expanded test-type keyword map ────────────────────────────────────────────
_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "cognitive":            ["ability", "aptitude", "cognitive", "numerical", "verbal",
                             "inductive", "deductive", "reasoning", "calculation"],
    "personality":          ["personality", "behavior", "behaviour", "opq", "dsi",
                             "motivational", "psych"],
    "knowledge":            ["knowledge", "skills", "technical", "professional",
                             "terminology", "vocabulary"],
    "simulation":           ["simulation", "exercise", "inbox", "in-tray"],
    "situational judgment": ["situational", "sjt", "biodata", "judgment"],
    "competency":           ["competen"],
}


def _compute_metadata_score(
    entry: AssessmentEntry,
    constraints: Dict[str, Any],
) -> float:
    """
    Structured metadata match score for a single catalog entry.
    Returns a float ≥ 0 (higher = better match against constraints).
    Negative contributions are applied only for clear mis-matches.
    """
    score = 0.0
    searchable = entry.searchable_text  # already lowercased in preprocess
    name_lower = entry.name.lower()

    # ── Language ──────────────────────────────────────────────────────────────
    lang = (constraints.get("language") or "").lower().strip()
    if lang and lang not in ("english",):          # English is default — no bonus
        entry_langs_str = " ".join(entry.languages).lower()
        if lang in ("bilingual", "multilingual"):
            # "bilingual" means the test must support more than one language.
            if len(entry.languages) > 1:
                score += _W_LANGUAGE
            # single-language entries are not wrong — just not boosted
        else:
            if lang in entry_langs_str:
                score += _W_LANGUAGE
            elif entry.languages:                  # languages listed but lang absent
                score -= _W_LANGUAGE * 0.4         # mild penalty, not disqualifying

    # ── Domain / Industry ─────────────────────────────────────────────────────
    domain = (constraints.get("domain") or "").lower().strip()
    if domain:
        words = [w for w in domain.replace("-", " ").split() if len(w) > 3]
        if any(w in searchable for w in words):
            score += _W_DOMAIN

    # ── Job role keywords ─────────────────────────────────────────────────────
    role = (constraints.get("job_role") or "").lower().strip()
    if role:
        role_words = [w for w in role.split() if len(w) > 3]
        matched = sum(1 for w in role_words if w in searchable)
        if matched:
            score += _W_ROLE * min(1.0, matched / max(1, len(role_words)))

    # ── Compliance topics ─────────────────────────────────────────────────────
    compliance = [c.lower() for c in (constraints.get("compliance_topics") or [])]
    if compliance:
        if any(topic in searchable or topic in name_lower for topic in compliance):
            score += _W_COMPLIANCE

    # ── Assessment / test type ────────────────────────────────────────────────
    test_types = [t.lower() for t in (constraints.get("test_types") or [])]
    if test_types:
        entry_text = " ".join(entry.keys).lower() + " " + searchable
        for tt in test_types:
            kws = _TYPE_KEYWORDS.get(tt, [tt])
            if any(kw in entry_text for kw in kws):
                score += _W_TEST_TYPE
                break   # one match is enough for the bonus

    # ── Job level / seniority ─────────────────────────────────────────────────
    level = (constraints.get("job_level") or constraints.get("seniority") or "").lower()
    if level and entry.job_levels:
        level_words = [w for w in level.split() if len(w) > 3]
        entry_levels_str = " ".join(entry.job_levels).lower()
        if any(w in entry_levels_str for w in level_words):
            score += _W_JOB_LEVEL

    return score


class ConstraintAwareRetriever:
    """
    Hybrid retriever that uses structured constraint matching as the primary
    precision signal. BM25 and embeddings provide broad recall; metadata
    scoring selects the right assessments from that recall pool.
    """

    def __init__(
        self,
        entries: List[AssessmentEntry],
        vector_store: VectorStore,
    ):
        self.entries = entries
        self.vector_store = vector_store
        self.entity_ids = [e.entity_id for e in entries]
        self._id_to_idx: Dict[str, int] = {
            eid: i for i, eid in enumerate(self.entity_ids)
        }
        self._id_to_entry: Dict[str, AssessmentEntry] = {
            e.entity_id: e for e in entries
        }

        tokenised = [e.searchable_text.split() for e in entries]
        self.bm25 = BM25Okapi(tokenised)
        logger.info("ConstraintAwareRetriever ready.")

    def retrieve(
        self,
        query: str,
        constraints: Dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> List[Tuple[str, float]]:
        """
        Returns [(entity_id, combined_score)] sorted descending.

        FinalScore = metadata_score
                   + BM25_norm  * _W_BM25
                   + embed_norm * _W_EMBED
        """
        top_k = top_k or settings.top_k_retrieve
        constraints = constraints or {}
        pool_size = top_k * 3   # wider recall pool before metadata scoring

        # ── 1. BM25 recall ────────────────────────────────────────────────────
        tokens = query.lower().split() if query.strip() else []
        has_signal = bool(tokens)
        if has_signal:
            bm25_raw = self.bm25.get_scores(tokens)
            max_bm25 = float(bm25_raw.max()) or 1.0
            bm25_norm = bm25_raw / max_bm25
        else:
            bm25_norm = np.zeros(len(self.entries))

        # ── 2. Embedding recall ───────────────────────────────────────────────
        sem_scores: Dict[str, float] = {}
        if has_signal:
            q_vec = embed_query(query)
            semantic_hits = self.vector_store.search(q_vec, pool_size)
            if semantic_hits:
                max_sem = max(s for _, s in semantic_hits) or 1.0
                sem_scores = {eid: s / max_sem for eid, s in semantic_hits}

        # ── 3. Candidate pool ─────────────────────────────────────────────────
        # With a real query: union of top BM25 + top semantic.
        # With no query (empty or stop-words only) but constraints present:
        # score every entry — metadata signal alone will differentiate.
        # With no query AND no constraints: return empty (caller handles clarification).
        if not has_signal and not constraints:
            logger.info("Empty query and no constraints — returning empty candidate set")
            return []

        if has_signal:
            top_bm25_idx = np.argsort(bm25_norm)[::-1][:pool_size]
            candidate_eids: set[str] = {self.entity_ids[i] for i in top_bm25_idx}
            candidate_eids.update(sem_scores.keys())
        else:
            # No text signal but constraints present — score everything
            candidate_eids = set(self.entity_ids)

        # ── 4. Score every candidate ──────────────────────────────────────────
        scored: Dict[str, float] = {}
        for eid in candidate_eids:
            idx = self._id_to_idx.get(eid)
            entry = self._id_to_entry.get(eid)
            if idx is None or entry is None:
                continue

            b_score = float(bm25_norm[idx]) * _W_BM25
            s_score = sem_scores.get(eid, 0.0) * _W_EMBED
            m_score = _compute_metadata_score(entry, constraints)

            scored[eid] = m_score + b_score + s_score

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)

        if ranked:
            top3 = [(self._id_to_entry[eid].name[:35], f"{sc:.2f}")
                    for eid, sc in ranked[:3] if eid in self._id_to_entry]
            logger.info(
                f"Retrieval: {len(ranked)} candidates → top {top_k} "
                f"| top3: {top3}",
            )

        return ranked[:top_k]


# Backward-compatible alias so main.py import still works during transition
HybridRetriever = ConstraintAwareRetriever
