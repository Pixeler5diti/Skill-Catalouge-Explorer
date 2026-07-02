"""
Build concise LLM prompts. Token-efficient: never sends the full catalog.

Prompt types:
  build_recommendation_prompt — main recommend/refine path
  build_clarification_prompt  — clarify intent
  build_refusal_prompt        — refuse intent (legal/OOB)
  build_comparison_prompt     — compare two assessments
"""
from typing import List, Dict, Any, Optional

from app.schemas import AssessmentEntry, Message

# ── Shared rules ──────────────────────────────────────────────────────────────

_SHARED_RULES = """You are an expert SHL assessment advisor.

HARD RULES:
- ONLY reference assessments from the CATALOG block provided below.
- NEVER invent assessment names, IDs, or URLs.
- NEVER answer from prior knowledge about specific SHL products not in the catalog.
- Do not answer legal, compliance, or HR-policy questions — refer to legal counsel.

Respond ONLY in this exact JSON format:
{
  "reply": "your conversational response",
  "selected_ids": ["3768", "4311"],
  "end_of_conversation": false
}

selected_ids rules:
- Use ONLY bare numeric IDs shown after "ID:" in the catalog (e.g. "3768", NOT "ID:3768").
- Include ONLY IDs from the CATALOG block below.
- Use [] when no recommendations are appropriate.
- Prefer 3–6 focused recommendations over exhaustive lists."""

_CATALOG_ENTRY_TEMPLATE = """[ID:{entity_id}] {name}
  Type: {test_type} | Duration: {duration} | Levels: {levels} | Languages: {langs}
  {description}"""


def _format_entry(entry: AssessmentEntry) -> str:
    return _CATALOG_ENTRY_TEMPLATE.format(
        entity_id=entry.entity_id,
        name=entry.name,
        test_type=entry.test_type or "Unknown",
        duration=entry.duration or "Not specified",
        levels=", ".join(entry.job_levels[:3]) if entry.job_levels else "All levels",
        langs=", ".join(entry.languages[:4]) if entry.languages else "See catalog",
        description=entry.description[:200] if entry.description else "",
    )


def _format_constraints(constraints: Dict[str, Any]) -> str:
    if not constraints:
        return "None"
    labels = {
        "job_role":          "Role",
        "job_level":         "Level",
        "seniority":         "Seniority",
        "domain":            "Industry/Domain",
        "language":          "Language",
        "test_types":        "Assessment types wanted",
        "exclude_types":     "Types to exclude",
        "skills":            "Skills/Competencies",
        "compliance_topics": "Compliance topics",
        "software_tools":    "Software/Tools",
        "max_duration_minutes": "Max duration (min)",
        "other":             "Other",
    }
    lines = []
    for key, label in labels.items():
        val = constraints.get(key)
        if val is None or val == "" or val == []:
            continue
        lines.append(
            f"  {label}: {', '.join(str(v) for v in val)}"
            if isinstance(val, list) else f"  {label}: {val}"
        )
    return "\n".join(lines) if lines else "None"


# ── Recommendation / Refinement prompt ───────────────────────────────────────

def build_recommendation_prompt(
    messages: List[Message],
    retrieved_entries: List[AssessmentEntry],
    constraints: Dict[str, Any],
    intent: str,
    conflict: Any = None,
) -> List[Dict[str, str]]:
    """
    Prompt for recommend and refine intents.

    The LLM receives:
      - Extracted constraints (so it understands the hiring context)
      - Conflict description (if any) — it must surface the tradeoff to the user
      - Retrieved catalog entries — the ONLY assessments it may recommend
      - Conversation history
      - Intent context hint

    The LLM's job: explain WHY these assessments fit. It does NOT select freely —
    it picks from selected_ids only within the provided catalog entries.
    """
    catalog_block = "\n\n".join(_format_entry(e) for e in retrieved_entries[:20])
    constraints_block = _format_constraints(constraints)

    conflict_block = ""
    if conflict:
        conflict_block = (
            f"\nCONFLICT TO SURFACE TO USER:\n{conflict.description}\n"
            "You must explain this tradeoff in your reply. "
            "Recommend what IS available and describe the hybrid option if applicable.\n"
        )

    intent_hint = {
        "recommend": "Recommend the most relevant assessments from the catalog below.",
        "refine":    (
            "The user is refining a previous recommendation. "
            "Honour ALL constraints including those from earlier turns — "
            "do not drop a constraint just because it was mentioned before."
        ),
    }.get(intent, "")

    system = (
        f"{_SHARED_RULES}\n\n"
        f"EXTRACTED HIRING CONSTRAINTS:\n{constraints_block}\n"
        f"{conflict_block}\n"
        f"AVAILABLE CATALOG ({len(retrieved_entries)} entries):\n{catalog_block}"
    )
    if intent_hint:
        system += f"\n\nCONTEXT: {intent_hint}"

    history = [{"role": m.role, "content": m.content} for m in messages[-10:]]
    return [{"role": "system", "content": system}] + history


# ── Clarification prompt ──────────────────────────────────────────────────────

_CLARIFY_SYSTEM = """You are an SHL assessment advisor.

You need more information before recommending assessments.

Ask EXACTLY ONE focused clarification question based on what is missing from
the constraints provided. Do not ask multiple questions at once.

Respond in this exact JSON format:
{
  "reply": "your single clarification question",
  "selected_ids": [],
  "end_of_conversation": false
}"""


def build_clarification_prompt(
    messages: List[Message],
    constraints: Dict[str, Any],
) -> List[Dict[str, str]]:
    constraints_block = _format_constraints(constraints)
    missing = _identify_missing(constraints)

    system = (
        f"{_CLARIFY_SYSTEM}\n\n"
        f"Constraints extracted so far:\n{constraints_block}\n\n"
        f"Most important missing information: {missing}"
    )
    history = [{"role": m.role, "content": m.content} for m in messages[-6:]]
    return [{"role": "system", "content": system}] + history


def _identify_missing(constraints: Dict[str, Any]) -> str:
    if not constraints.get("job_role"):
        return "job role or position being hired for"
    if not constraints.get("domain") and not constraints.get("industry"):
        return "industry or business domain"
    if not constraints.get("test_types") and not constraints.get("skills"):
        return "type of assessment needed (cognitive, personality, knowledge, etc.)"
    return "any additional context to narrow down the recommendations"


# ── Refusal prompt ────────────────────────────────────────────────────────────

_REFUSAL_SYSTEM = """You are an SHL assessment advisor.

The user has asked a question outside your scope: either a legal/compliance
question or something unrelated to assessment selection.

Rules:
- Do NOT provide legal advice or compliance requirements.
- You MAY describe what a named assessment MEASURES (using catalog data only).
- You MAY NOT state whether any assessment is legally required.
- Politely redirect to assessment selection.

Respond in this exact JSON format:
{
  "reply": "your polite refusal and optional factual description of assessment purpose",
  "selected_ids": [],
  "end_of_conversation": false
}"""


def build_refusal_prompt(
    messages: List[Message],
    constraints: Dict[str, Any],
    by_id: Dict[str, AssessmentEntry],
) -> List[Dict[str, str]]:
    # Find any named assessments in the last user message for factual description
    last_content = messages[-1].content if messages else ""
    relevant_entries = _find_named_entries(last_content, by_id)

    catalog_snippet = ""
    if relevant_entries:
        catalog_snippet = "\n\nRELEVANT CATALOG ENTRIES (for factual description only):\n"
        catalog_snippet += "\n".join(_format_entry(e) for e in relevant_entries[:2])

    system = f"{_REFUSAL_SYSTEM}{catalog_snippet}"
    history = [{"role": m.role, "content": m.content} for m in messages[-4:]]
    return [{"role": "system", "content": system}] + history


def _find_named_entries(
    text: str, by_id: Dict[str, AssessmentEntry]
) -> List[AssessmentEntry]:
    text_lower = text.lower()
    found = []
    for entry in by_id.values():
        if entry.name.lower() in text_lower or any(
            word in text_lower
            for word in entry.name.lower().split()
            if len(word) > 4
        ):
            found.append(entry)
    return found[:2]


# ── Comparison prompt ─────────────────────────────────────────────────────────

def build_comparison_prompt(
    messages: List[Message],
    assessment_a: AssessmentEntry,
    assessment_b: AssessmentEntry,
) -> List[Dict[str, str]]:
    """Prompt for comparing two specific assessments. No retrieval needed."""
    a_text = _format_entry(assessment_a)
    b_text = _format_entry(assessment_b)
    system = (
        f"{_SHARED_RULES}\n\n"
        f"ASSESSMENT A:\n{a_text}\n\n"
        f"ASSESSMENT B:\n{b_text}\n\n"
        "Compare ONLY using the information above. "
        "Cover: purpose, duration, languages, test type, target competencies. "
        "Be concise and specific."
    )
    history = [{"role": m.role, "content": m.content} for m in messages[-6:]]
    return [{"role": "system", "content": system}] + history
