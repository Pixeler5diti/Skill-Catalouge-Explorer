"""
Rule-based reranker with domain+compliance combination rules.

Operates on top of retrieval scores — never hardcodes final answers.
Rules add or subtract points; the ranking decides what the LLM sees.
"""
from __future__ import annotations

import re
from typing import List, Dict, Tuple, Any

from app.schemas import AssessmentEntry
from app.config import settings
from app.utils.logger import logger


# ── Domain + trigger + name-match rules ──────────────────────────────────────
# Structure: (domain_keywords, trigger_keywords, name_fragments_to_boost, boost)
# A rule fires when:
#   - any domain_keyword appears in the request domain/role
#   - any trigger_keyword appears in compliance/skills/domain
#   - any name_fragment matches the entry name or searchable text
_DOMAIN_RULES: List[Tuple[List[str], List[str], List[str], float]] = [
    # Healthcare + HIPAA / privacy compliance
    (
        ["healthcare", "medical", "health", "clinical", "hospital",
         "pharma", "pharmaceutical", "nursing"],
        ["hipaa", "compliance", "privacy", "regulation", "regulatory"],
        ["hipaa", "health insurance portability", "medical compliance"],
        7.0,
    ),
    # Healthcare + clinical / medical terminology
    (
        ["healthcare", "medical", "health", "clinical", "nursing", "hospital"],
        ["terminology", "vocabulary", "language", "terms", "jargon"],
        ["medical terminology", "clinical terminology", "health terminology",
         "medical vocabulary"],
        7.0,
    ),
    # Finance + regulatory / audit compliance
    (
        ["finance", "financial", "banking", "investment", "accounting", "audit"],
        ["sox", "sarbanes", "compliance", "regulation", "audit", "gaap", "ifrs"],
        ["sox", "sarbanes", "financial compliance", "audit", "gaap"],
        6.0,
    ),
    # Legal terminology
    (
        ["legal", "law", "attorney", "paralegal", "compliance", "contracts"],
        ["terminology", "vocabulary", "language", "terms"],
        ["legal terminology", "legal vocabulary", "legal language"],
        7.0,
    ),
    # Retail / customer service
    (
        ["retail", "customer service", "hospitality", "call centre", "call center"],
        ["service", "customer", "sales", "communication"],
        ["customer service", "retail", "contact centre", "sales ability"],
        4.0,
    ),
    # Logistics / supply chain
    (
        ["logistics", "supply chain", "warehouse", "operations", "procurement"],
        ["operations", "process", "efficiency"],
        ["supply chain", "logistics", "operations", "warehouse"],
        4.0,
    ),
]

# Personality-related assessment name fragments
_PERSONALITY_FRAGMENTS = [
    "opq32r", "opq32", "opq", "dsi", "personality",
    "behaviour", "behavior", "motivational questionnaire",
    "mqm5", "global personality", "psych",
]

# Cognitive / ability test fragments
_COGNITIVE_FRAGMENTS = [
    "verify", "numerical reasoning", "verbal reasoning", "inductive",
    "deductive", "calculation", "checking", "cognitive",
    "aptitude", "ability", "graduate", "management",
]

# Situational judgment / biodata
_SJT_FRAGMENTS = [
    "situational", "sjt", "judgment", "biodata",
]

# Hybrid = cognitive + personality together
_HYBRID_FRAGMENTS = _PERSONALITY_FRAGMENTS + _COGNITIVE_FRAGMENTS


def _tok(text: str) -> str:
    """Lowercase and strip for matching."""
    return text.lower().strip()


def _hits(text: str, fragments: List[str]) -> bool:
    return any(f in text for f in fragments)


def rerank(
    candidates: List[Tuple[str, float]],
    entries_by_id: Dict[str, AssessmentEntry],
    constraints: Dict[str, Any],
    top_k: int | None = None,
) -> List[str]:
    """
    Apply rule-based boosts on top of retrieval scores.
    Returns an ordered list of entity_ids (best first), length ≤ top_k.
    """
    top_k = top_k or settings.top_k_return

    domain     = _tok(constraints.get("domain") or "")
    role       = _tok(constraints.get("job_role") or "")
    lang       = _tok(constraints.get("language") or "")
    test_types = [_tok(t) for t in (constraints.get("test_types") or [])]
    compliance = [_tok(c) for c in (constraints.get("compliance_topics") or [])]
    skills     = [_tok(s) for s in (constraints.get("skills") or [])]
    max_dur    = constraints.get("max_duration_minutes")

    # Derived intent flags from the full constraint set
    all_text = " ".join([domain, role, lang] + test_types + skills)
    wants_personality = any(
        kw in all_text
        for kw in ["personality", "behaviour", "behavior", "opq", "dsi", "motivational"]
    ) or "personality" in test_types
    wants_cognitive = any(
        kw in all_text
        for kw in ["cognitive", "ability", "aptitude", "numerical", "verbal", "reasoning"]
    ) or "cognitive" in test_types
    wants_sjt = any(
        kw in all_text
        for kw in ["situational", "sjt", "judgment", "biodata"]
    ) or "situational judgment" in test_types
    wants_hybrid = (
        "hybrid" in all_text
        or ("personality" in test_types and "cognitive" in test_types)
        or (wants_personality and wants_cognitive)
    )
    # Language requirement flags
    wants_bilingual     = lang in ("bilingual", "multilingual") or "bilingual" in all_text
    needs_specific_lang = bool(lang) and lang not in ("", "english", "bilingual", "multilingual")

    rescored: List[Tuple[str, float]] = []

    for entity_id, base_score in candidates:
        entry = entries_by_id.get(entity_id)
        if not entry:
            continue

        name_lower   = entry.name.lower()
        searchable   = entry.searchable_text     # already lowercase
        entry_langs  = " ".join(entry.languages).lower()
        boost        = 0.0

        # ── Domain + compliance combination rules ──────────────────────────
        for domain_kws, trigger_kws, name_frags, rule_boost in _DOMAIN_RULES:
            domain_match = any(kw in domain or kw in role for kw in domain_kws)
            if not domain_match:
                continue
            trigger_context = " ".join(compliance + skills) + " " + domain
            trigger_match = any(kw in trigger_context for kw in trigger_kws)
            if not trigger_match:
                continue
            if _hits(name_lower, name_frags) or _hits(searchable, name_frags):
                boost += rule_boost
                logger.debug(f"Domain rule +{rule_boost} → {entry.name[:40]}")

        # ── Personality shortlisting ───────────────────────────────────────
        # Check both name and searchable_text — some entries only signal
        # personality via description/keys, not in their short display name.
        if wants_personality and (
            _hits(name_lower, _PERSONALITY_FRAGMENTS)
            or _hits(searchable, _PERSONALITY_FRAGMENTS)
        ):
            boost += 5.0

        # ── Cognitive shortlisting ─────────────────────────────────────────
        if wants_cognitive and (
            _hits(name_lower, _COGNITIVE_FRAGMENTS)
            or _hits(searchable, _COGNITIVE_FRAGMENTS)
        ):
            boost += 3.0

        # ── SJT shortlisting ──────────────────────────────────────────────
        if wants_sjt and (
            _hits(name_lower, _SJT_FRAGMENTS)
            or _hits(searchable, _SJT_FRAGMENTS)
        ):
            boost += 4.0

        # ── Hybrid: both personality and cognitive wanted ──────────────────
        if wants_hybrid:
            is_personality = _hits(name_lower, _PERSONALITY_FRAGMENTS) or _hits(searchable, _PERSONALITY_FRAGMENTS)
            is_cognitive   = _hits(name_lower, _COGNITIVE_FRAGMENTS)   or _hits(searchable, _COGNITIVE_FRAGMENTS)
            if is_personality or is_cognitive:
                boost += 2.0   # extra nudge for assessments that fit either side

        # ── Language preference ────────────────────────────────────────────
        if wants_bilingual:
            # "bilingual" → reward assessments available in multiple languages
            if len(entry.languages) > 1:
                boost += 6.0
            # single-language entries are not penalised — just not rewarded
        elif needs_specific_lang:
            # specific non-English language required
            if lang in entry_langs:
                boost += 6.0
            elif entry.languages and "english" in entry_langs and len(entry.languages) == 1:
                # English-only when another language is explicitly required
                boost -= 4.0

        # ── Skills keyword matches ─────────────────────────────────────────
        if skills:
            matched = sum(1 for s in skills if len(s) > 3 and s in searchable)
            boost += matched * 1.5

        # ── Duration filter ────────────────────────────────────────────────
        if max_dur and entry.duration:
            try:
                digits = re.findall(r"\d+", entry.duration)
                if digits:
                    dur_val = int(digits[0])
                    if dur_val > int(max_dur):
                        boost -= 3.0
            except (ValueError, TypeError):
                pass

        rescored.append((entity_id, base_score + boost))

    rescored.sort(key=lambda x: x[1], reverse=True)

    if rescored:
        top3 = [
            (entries_by_id[eid].name[:35], f"{sc:.2f}")
            for eid, sc in rescored[:3]
            if eid in entries_by_id
        ]
        logger.info(f"Reranked {len(rescored)} → top {top_k} | top3: {top3}")

    return [eid for eid, _ in rescored[:top_k]]
