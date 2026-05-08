"""Thin wrapper over ai_client.summarize_text."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def summarize_file(file_path: Path) -> str | None:
    """Extract text from file_path and generate a summary. Returns markdown string or None."""
    from src.extractor import extract_text, count_words
    from src.ai_client import summarize_text, estimate_cost
    import config

    text = extract_text(file_path)
    if not text:
        logger.warning(f"Sin texto extraíble: {file_path.name}")
        return None

    word_count = count_words(text)
    cost, pdfs_remaining = estimate_cost(word_count)

    if config.PROVIDER == "groq":
        logger.info(f"  Palabras: {word_count:,} | PDFs restantes hoy: ~{pdfs_remaining}")
    else:
        logger.info(f"  Palabras: {word_count:,} | Costo: ~${cost:.4f} USD")

    summary = summarize_text(text, document_name=file_path.name)
    if not summary:
        logger.error(f"  Sin respuesta de la API para {file_path.name}")
    return summary
