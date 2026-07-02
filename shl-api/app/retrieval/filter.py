"""
Rule-based pre-retrieval filter.
Applied BEFORE score-based reranking. Deterministic — no LLM, no embeddings.

Responsibilities:
  1. Language hard-filter: when a specific non-English language is required
     and no conflict is present, remove assessments that don't support it.
  2. Domain boost rules: boost entries whose names/content match domain-specific
     signals (healthcare → HIPAA; finance → numerical reasoning; etc.).
  3. Skills/tools keyword boost.
"""
from __future__ import annotations

from typing import List, Dict, Tuple, Any, Optional, TYPE_CHECKING

from app.schemas import AssessmentEntry
from app.utils.logger import logger

if TYPE_CHECKING:
    from app.conversation.planner import Conflict


def _tok(text: str) -> str:
    return text.lower().strip()


def _hits(haystack: str, needles: List[str]) -> bool:
    return any(n in haystack for n in needles)


# ── Domain boost rules ────────────────────────────────────────────────────────
# Structure: (domain_context_keywords, trigger_keywords, entry_name_fragments, boost)
# A rule fires when:
#   - Any domain_context_keyword appears in the domain/role/skills context
#   - trigger_keywords is empty OR any trigger_keyword also appears in context
#   - Any entry_name_fragment matches the entry name or searchable_text
#
# Boosts are large (8-10) so they dominate the retrieval score for specific matches.

_DOMAIN_BOOST_RULES: List[Tuple[List[str], List[str], List[str], float]] = [
    # Healthcare + HIPAA compliance
    (
        ["healthcare", "medical", "health", "clinical", "hospital",
         "patient", "nursing", "pharma", "pharmaceutical"],
        ["hipaa", "compliance", "privacy", "regulation", "patient records",
         "protected health"],
        ["hipaa", "health insurance portability"],
        10.0,
    ),
    # Healthcare + medical terminology
    (
        ["healthcare", "medical", "health", "clinical", "nursing",
         "hospital", "pharma"],
        ["terminology", "vocabulary", "terms", "jargon", "language"],
        ["medical terminology", "clinical terminology", "health terminology",
         "medical vocabulary"],
        10.0,
    ),
    # Patient records — HIPAA specific
    (
        ["patient records", "patient data", "ehr", "electronic health record",
         "phi", "protected health"],
        [],  # domain alone is specific enough
        ["hipaa", "health insurance portability"],
        12.0,
    ),
    # Finance — numerical reasoning
    (
        ["finance", "financial", "banking", "investment", "accounting",
         "treasury", "audit"],
        [],
        ["numerical reasoning", "numerical ability", "calculation",
         "financial numeracy"],
        6.0,
    ),
    # Finance — Excel / spreadsheet skills
    (
        ["finance", "financial", "banking", "accounting", "analyst"],
        ["excel", "spreadsheet", "data analysis", "modelling"],
        ["excel", "spreadsheet", "microsoft office", "ms office"],
        8.0,
    ),
    # Java / software engineering
    (
        ["java", "software", "developer", "engineering", "tech",
         "backend", "programming"],
        ["java"],
        ["java"],
        9.0,
    ),
    # Legal terminology
    (
        ["legal", "law", "attorney", "paralegal", "counsel",
         "contracts", "compliance officer"],
        ["terminology", "vocabulary"],
        ["legal terminology", "legal vocabulary", "legal language"],
        9.0,
    ),
    # Retail / customer service
    (
        ["retail", "customer service", "hospitality", "call centre",
         "call center", "contact centre"],
        ["service", "customer", "sales"],
        ["customer service", "retail", "contact centre", "sales ability",
         "customer contact"],
        5.0,
    ),
    # Logistics / supply chain
    (
        ["logistics", "supply chain", "warehouse", "operations",
         "procurement", "inventory"],
        [],
        ["supply chain", "logistics", "operations management",
         "warehouse"],
        5.0,
    ),
]


def apply_domain_rules(
    candidates: List[Tuple[str, float]],
    constraints: Dict[str, Any],
    entries_by_id: Dict[str, AssessmentEntry],
    conflict: Optional["Conflict"] = None,
) -> List[Tuple[str, float]]:
    """
    Apply rule-based boosts and language hard-filter to the candidate list.

    Returns a re-scored (possibly shorter) candidate list sorted descending.
    """
    domain = _tok(constraints.get("domain") or "")
    role   = _tok(constraints.get("job_role") or "")
    lang   = _tok(constraints.get("language") or "")
    skills = [_tok(s) for s in (constraints.get("skills") or [])]
    tools  = [_tok(t) for t in (constraints.get("software_tools") or [])]
    comp   = [_tok(c) for c in (constraints.get("compliance_topics") or [])]

    # Build full context string for rule matching
    context = " ".join(filter(None, [domain, role] + skills + tools + comp))

    # ── Language hard-filter ──────────────────────────────────────────────────
    # Keep only assessments supporting the required language.
    # Skip if: language is English/bilingual, or a conflict means no lang-specific
    # knowledge tests exist (we still want to show what's available).
    specific_lang = (
        bool(lang)
        and lang not in ("", "english", "bilingual", "multilingual")
        and conflict is None
    )

    if specific_lang:
        before = len(candidates)
        filtered = [
            (eid, sc) for eid, sc in candidates
            if eid in entries_by_id
            and any(lang in l.lower() for l in entries_by_id[eid].languages)
        ]
        if filtered:
            logger.info(
                f"Language hard-filter ({lang}): {before} → {len(filtered)} candidates"
            )
            candidates = filtered
        else:
            # Filter would remove everything — conflict should have caught this,
            # but as a safety net keep the full list and log a warning.
            logger.warning(
                f"Language filter ({lang}) would remove all candidates — keeping full set. "
                "Consider flagging this as a conflict upstream."
            )

    # ── Domain boost rules ────────────────────────────────────────────────────
    rescored: List[Tuple[str, float]] = []

    for eid, base_score in candidates:
        entry = entries_by_id.get(eid)
        if not entry:
            continue

        boost      = 0.0
        name_lo    = entry.name.lower()
        searchable = entry.searchable_text

        for domain_kws, trigger_kws, name_frags, rule_boost in _DOMAIN_BOOST_RULES:
            if not _hits(context, domain_kws):
                continue
            if trigger_kws and not _hits(context, trigger_kws):
                continue
            if _hits(name_lo, name_frags) or _hits(searchable, name_frags):
                boost += rule_boost
                logger.debug(f"Filter +{rule_boost:.0f} → {entry.name[:40]}")

        # ── Skills / tools exact keyword boost ─────────────────────────────
        for kw in skills + tools:
            if len(kw) > 3 and (kw in name_lo or kw in searchable):
                boost += 3.0

        rescored.append((eid, base_score + boost))

    rescored.sort(key=lambda x: x[1], reverse=True)

    if rescored:
        top3 = [
            (entries_by_id[eid].name[:30], f"{sc:.1f}")
            for eid, sc in rescored[:3]
            if eid in entries_by_id
        ]
        logger.info(f"Post-filter top3: {top3}")

    return rescored
