"""Load the raw SHL catalog JSON from disk."""
import json
from pathlib import Path
from typing import List, Dict, Any
from app.utils.logger import logger


def _sanitise_json(raw: str) -> str:
    """
    Remove invalid control characters that appear INSIDE JSON string values.
    The catalog has literal newlines/carriage-returns embedded in some field
    values (e.g. 'Microsoft \\n    365'), which are illegal in JSON strings.
    Uses a minimal state machine so it never corrupts the JSON structure.
    """
    result: list[str] = []
    in_string = False
    escape_next = False

    for ch in raw:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ch in ("\n", "\r", "\t", "\x0b", "\x0c"):
            # Replace bare control chars inside strings with a single space
            result.append(" ")
        elif in_string and ord(ch) < 0x20:
            # Other control chars inside strings → drop
            pass
        else:
            result.append(ch)

    return "".join(result)


def load_catalog(path: str) -> List[Dict[str, Any]]:
    """
    Load and return the raw catalog entries from the JSON file.
    Raises FileNotFoundError if the path doesn't exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Catalog file not found: {path}")

    raw = p.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    raw = _sanitise_json(raw)
    entries = json.loads(raw)
    if not isinstance(entries, list):
        raise ValueError("Catalog JSON root must be an array.")

    logger.info(f"Loaded {len(entries)} raw catalog entries from {path}")
    return entries
