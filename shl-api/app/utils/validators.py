"""Validate LLM outputs before returning to caller."""
from typing import List, Dict
from app.schemas import Recommendation


def validate_recommendations(
    recs: List[Recommendation],
    catalog_by_id: Dict[str, dict],
    catalog_by_name: Dict[str, dict],
) -> List[Recommendation]:
    """
    Remove any recommendation that cannot be found in the catalog.
    Caps at 10 items.
    """
    valid: List[Recommendation] = []
    for r in recs:
        # Verify name exists and URL matches
        entry = catalog_by_name.get(r.name.strip().lower())
        if entry and entry["url"] == r.url:
            valid.append(r)
        elif entry:
            # Correct the URL if it drifted
            valid.append(Recommendation(
                name=r.name,
                url=entry["url"],
                test_type=entry["test_type"],
            ))
    return valid[:10]


def entity_ids_to_recommendations(
    entity_ids: List[str],
    catalog_by_id: Dict[str, dict],
) -> List[Recommendation]:
    """Map entity IDs from LLM response to validated Recommendation objects."""
    recs: List[Recommendation] = []
    seen: set = set()
    for raw_eid in entity_ids:
        # Strip any prefix the LLM may echo (e.g. "ID:3768" → "3768")
        eid = str(raw_eid).strip()
        if eid.upper().startswith("ID:"):
            eid = eid[3:].strip()
        if not eid or eid in seen:
            continue
        entry = catalog_by_id.get(eid)
        if entry:
            recs.append(Recommendation(
                name=entry["name"],
                url=entry["url"],
                test_type=entry["test_type"],
            ))
            seen.add(eid)
    return recs[:10]
