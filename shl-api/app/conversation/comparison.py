"""
Assessment comparison handler.
Direct catalog lookup by name — no embeddings for comparison intent.
Falls back to retriever search only when exact name is not found.
"""
import json
import re
from typing import List, Optional, Tuple, Dict, TYPE_CHECKING

from app.schemas import Message, AssessmentEntry
from app.conversation.prompt_builder import build_comparison_prompt
from app.llm.groq_client import chat_completion
from app.utils.logger import logger

if TYPE_CHECKING:
    from app.retrieval.retriever import ConstraintAwareRetriever


def _extract_assessment_names(messages: List[Message]) -> List[str]:
    """
    Extract two assessment names from the last user message.
    Tries quoted names first, then splits on comparison conjunctions.
    """
    last = messages[-1].content
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', last)
    names = [q[0] or q[1] for q in quoted if q[0] or q[1]]
    if len(names) >= 2:
        return names[:2]
    parts = re.split(r"\s+(?:and|vs\.?|versus|or)\s+", last, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return [p.strip() for p in parts[:2]]
    return []


def _find_entry(
    name: str,
    retriever: "ConstraintAwareRetriever",
    by_id: Dict[str, AssessmentEntry],
    by_name: Dict[str, AssessmentEntry],
) -> Optional[AssessmentEntry]:
    """
    Look up an assessment. Priority:
      1. Exact name match (no retrieval).
      2. Partial name match in catalog (no retrieval).
      3. Retriever search as last resort.
    """
    # 1. Exact match
    entry = by_name.get(name.lower())
    if entry:
        return entry

    # 2. Partial match — scan catalog names directly
    name_lower = name.lower()
    for entry in by_id.values():
        if name_lower in entry.name.lower() or entry.name.lower() in name_lower:
            return entry

    # 3. Fallback: retriever (passes constraints={} so no metadata scoring)
    hits = retriever.retrieve(name, constraints={}, top_k=3)
    for eid, _ in hits:
        candidate = by_id.get(eid)
        if candidate and name_lower in candidate.name.lower():
            return candidate
    if hits:
        return by_id.get(hits[0][0])
    return None


def handle_comparison(
    messages: List[Message],
    retriever: "ConstraintAwareRetriever",
    by_id: Dict[str, AssessmentEntry],
    by_name: Dict[str, AssessmentEntry],
) -> Tuple[str, List[str]]:
    """
    Handle a compare intent.
    Returns (reply_text, [entity_id_a, entity_id_b]).
    """
    names = _extract_assessment_names(messages)
    if len(names) < 2:
        return (
            "Which two assessments would you like me to compare? "
            "Please name them explicitly, e.g. \"Compare OPQ32r and Verify G+\".",
            [],
        )

    entry_a = _find_entry(names[0], retriever, by_id, by_name)
    entry_b = _find_entry(names[1], retriever, by_id, by_name)

    if not entry_a or not entry_b:
        missing = [n for n, e in zip(names, [entry_a, entry_b]) if not e]
        return (
            f"I couldn't find {', '.join(missing)} in the catalog. "
            "Please check the names and try again.",
            [],
        )

    logger.info(f"Comparing: {entry_a.name} vs {entry_b.name}")

    prompt_msgs = build_comparison_prompt(messages, entry_a, entry_b)
    raw = chat_completion(
        messages=prompt_msgs,
        max_tokens=600,
        temperature=0.1,
        json_mode=True,
    )
    try:
        parsed = json.loads(raw)
        reply = parsed.get("reply", raw)
        return reply, [entry_a.entity_id, entry_b.entity_id]
    except Exception:
        return raw, [entry_a.entity_id, entry_b.entity_id]
