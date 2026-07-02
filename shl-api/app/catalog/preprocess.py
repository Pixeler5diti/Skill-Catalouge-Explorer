"""
Normalize raw catalog entries into AssessmentEntry objects.
Builds searchable text, deduplicates, and creates lookup dicts.
"""
from typing import List, Dict, Any, Tuple
from app.schemas import AssessmentEntry
from app.utils.logger import logger

# Short abbreviation map for display
_KEY_ABBR: Dict[str, str] = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}


# Expand category keys with domain synonyms so BM25/metadata scoring has
# richer signal without relying on embedding similarity alone.
_KEY_SYNONYMS: Dict[str, str] = {
    "Ability & Aptitude":          "cognitive ability aptitude reasoning numerical verbal inductive deductive",
    "Personality & Behavior":      "personality behavior behaviour trait opq dsi motivational",
    "Knowledge & Skills":          "knowledge skills technical professional terminology vocabulary",
    "Biodata & Situational Judgment": "biodata situational judgment sjt scenario",
    "Assessment Exercises":        "exercise simulation inbox in-tray assessment centre",
    "Competencies":                "competency competencies leadership management",
    "Development & 360":           "development 360 feedback coaching",
    "Simulations":                 "simulation exercise virtual",
}


def _build_searchable_text(entry: Dict[str, Any]) -> str:
    """
    Combine all useful fields into a single lowercased search document.
    Category keys are expanded with domain synonyms to improve BM25 recall
    and metadata scoring without relying on embedding similarity alone.
    """
    keys: List[str] = entry.get("keys") or []
    key_synonyms = " ".join(_KEY_SYNONYMS.get(k, "") for k in keys)

    # Expand language names: strip locale qualifiers for broader matching
    # e.g. "Spanish (Latin America)" → also index as "spanish"
    languages: List[str] = entry.get("languages") or []
    lang_text = " ".join(languages)
    lang_simple = " ".join(
        lang.split("(")[0].strip().lower() for lang in languages
    )

    parts = [
        entry.get("name", ""),
        entry.get("description", ""),
        " ".join(keys),
        key_synonyms,
        " ".join(entry.get("job_levels", [])),
        lang_text,
        lang_simple,
        entry.get("duration", ""),
        "remote" if entry.get("remote") == "yes" else "",
        "adaptive" if entry.get("adaptive") == "yes" else "",
    ]
    return " ".join(p for p in parts if p).lower()


def _test_type_display(keys: List[str]) -> str:
    """Full display string for test_type field."""
    return ", ".join(keys) if keys else "Unknown"


def preprocess_catalog(
    raw: List[Dict[str, Any]],
) -> Tuple[
    List[AssessmentEntry],
    Dict[str, AssessmentEntry],   # by entity_id
    Dict[str, AssessmentEntry],   # by lowercase name
]:
    """
    Normalize, deduplicate, and index catalog entries.
    Returns (entries, by_id, by_name).
    """
    by_id: Dict[str, AssessmentEntry] = {}
    by_name: Dict[str, AssessmentEntry] = {}
    duplicates = 0

    for raw_entry in raw:
        entity_id = str(raw_entry.get("entity_id", "")).strip()
        name = (raw_entry.get("name") or "").strip()
        link = (raw_entry.get("link") or "").strip()

        # Skip entries with missing critical fields
        if not entity_id or not name or not link:
            continue

        # Deduplicate by entity_id
        if entity_id in by_id:
            duplicates += 1
            continue

        # Skip entries with bad status
        if raw_entry.get("status", "ok") != "ok":
            continue

        keys = raw_entry.get("keys") or []
        job_levels = raw_entry.get("job_levels") or []
        languages = raw_entry.get("languages") or []
        duration = (raw_entry.get("duration") or "").strip()
        description = (raw_entry.get("description") or "").strip()

        entry = AssessmentEntry(
            entity_id=entity_id,
            name=name,
            url=link,
            description=description,
            keys=keys,
            job_levels=job_levels,
            languages=languages,
            duration=duration,
            remote=raw_entry.get("remote", ""),
            adaptive=raw_entry.get("adaptive", ""),
            test_type=_test_type_display(keys),
            searchable_text=_build_searchable_text(raw_entry),
        )

        by_id[entity_id] = entry
        by_name[name.lower()] = entry

    entries = list(by_id.values())
    logger.info(
        f"Preprocessed {len(entries)} unique entries "
        f"({duplicates} duplicates removed)"
    )
    return entries, by_id, by_name
