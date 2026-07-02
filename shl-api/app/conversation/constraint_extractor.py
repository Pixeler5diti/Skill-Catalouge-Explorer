"""
Extract hiring constraints from the full conversation history.
Returns a structured dict used for metadata-weighted retrieval and reranking.
"""
import json
from typing import List, Dict, Any
from app.schemas import Message
from app.llm.groq_client import chat_completion
from app.utils.logger import logger

_SYSTEM = """You extract hiring constraints from a conversation about SHL assessments.
Return ONLY valid JSON with these keys (omit keys whose values are genuinely unknown):
{
  "job_role": "the role being hired for",
  "job_level": "seniority level (entry, graduate, mid, manager, director, executive)",
  "language": "required assessment language if mentioned (e.g. Spanish, English, Bilingual)",
  "test_types": ["types wanted: cognitive, personality, knowledge, simulation, competency, situational judgment"],
  "max_duration_minutes": number or null,
  "domain": "industry/domain (healthcare, finance, tech, retail, logistics, legal, education, government)",
  "skills": ["specific skills, topics or competencies mentioned"],
  "compliance_topics": ["HIPAA, GDPR, SOX, PCI-DSS, or any compliance/regulatory topics mentioned"],
  "software_tools": ["specific software or tools mentioned e.g. Excel, SAP, Python"],
  "seniority": "entry|graduate|mid|manager|director|executive",
  "exclude_types": ["test types to exclude"],
  "other": "any other relevant constraint not captured above"
}
Rules:
- Read the ENTIRE conversation — accumulate all constraints mentioned across all turns
- When a user refines (e.g. "add personality", "go with hybrid", "make it shorter") merge
  the new constraint into previously established ones — do not discard earlier context
- Return only JSON, no extra text or markdown."""


def extract_constraints(messages: List[Message]) -> Dict[str, Any]:
    """
    Analyse the full conversation and return accumulated constraints.
    Always uses all messages so refinements never lose earlier context.
    """
    conv = "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)
    prompt_msgs = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Conversation:\n{conv}"},
    ]
    try:
        raw = chat_completion(
            messages=prompt_msgs,
            max_tokens=400,
            temperature=0.0,
            json_mode=True,
        )
        constraints = json.loads(raw)
        logger.info(f"Constraints extracted: {list(constraints.keys())}")
        return constraints
    except Exception as e:
        logger.error(f"Constraint extraction failed: {e}")
        return {}


def merge_constraints(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two constraint dicts.
    - Scalar values: updates override base.
    - List values: unioned (no duplicates, base order preserved first).
    - Empty / None / [] in updates never clobber a non-empty base value.
    """
    merged = dict(base)
    for k, v in updates.items():
        if v is None or v == "" or v == []:
            continue
        base_val = merged.get(k)
        if isinstance(v, list) and isinstance(base_val, list):
            merged[k] = base_val + [x for x in v if x not in base_val]
        else:
            merged[k] = v
    return merged


def constraints_to_query(constraints: Dict[str, Any]) -> str:
    """
    Build a natural-language retrieval query from extracted constraints.
    Used as input to BM25 and embedding recall — not for scoring.
    """
    parts: List[str] = []
    if constraints.get("job_role"):
        parts.append(f"{constraints['job_role']} assessment")
    if constraints.get("domain"):
        parts.append(constraints["domain"])
    if constraints.get("skills"):
        parts.extend(constraints["skills"])
    if constraints.get("test_types"):
        parts.extend(constraints["test_types"])
    if constraints.get("job_level") or constraints.get("seniority"):
        parts.append(constraints.get("job_level") or constraints.get("seniority", ""))
    if constraints.get("language"):
        parts.append(f"{constraints['language']} language")
    if constraints.get("compliance_topics"):
        parts.extend(constraints["compliance_topics"])
    if constraints.get("software_tools"):
        parts.extend(constraints["software_tools"])
    if constraints.get("other"):
        parts.append(constraints["other"])
    return " ".join(p for p in parts if p)
