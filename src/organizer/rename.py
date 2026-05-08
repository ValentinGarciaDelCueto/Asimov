"""Filename normalization: strip accents, illegal chars, cap length."""

import re
import unicodedata
from pathlib import Path


def normalize_filename(original: str, suffix: str | None = None) -> str:
    """
    Return a safe, normalized filename.
    - Strip accents/diacritics
    - Replace illegal filesystem chars with '_'
    - Collapse whitespace
    - Truncate stem to 100 chars (preserves extension)
    """
    p = Path(original)
    stem = p.stem
    ext = suffix if suffix is not None else p.suffix.lower()

    # Strip diacritics
    nfkd = unicodedata.normalize("NFKD", stem)
    stem = "".join(c for c in nfkd if not unicodedata.combining(c))

    # Replace illegal chars
    stem = re.sub(r'[\\/:*?"<>|]', "_", stem)
    stem = re.sub(r'\s+', " ", stem).strip()
    stem = stem[:100]

    return f"{stem}{ext}"
