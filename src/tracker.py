"""Registro de archivos procesados — evita reprocesar el mismo documento."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def load_processed(log_path: Path) -> dict:
    if not log_path.exists():
        return {}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"No se pudo cargar el registro: {e}. Iniciando vacío.")
        return {}


def save_processed(log_path: Path, processed: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"No se pudo guardar el registro: {e}")


def is_processed(file_path: Path, processed: dict) -> bool:
    """Return True if file was already summarized and content hasn't changed."""
    file_key = str(file_path.resolve())
    if file_key not in processed:
        return False

    entry = processed[file_key]

    # Legacy entries (only have "processed_at") count as processed if hash matches
    current_hash = _file_hash(file_path)
    stored_hash = entry.get("hash", "")
    if current_hash != stored_hash:
        logger.info(f"Archivo modificado, se volverá a procesar: {file_path.name}")
        return False

    # New entries: must have been summarized (have summarized_at)
    if "summarized_at" in entry:
        return entry["summarized_at"] is not None

    # Legacy entry with matching hash: treat as processed
    return True



def mark_organized(orig_path: Path, dest_path: Path, processed: dict) -> None:
    """Record that a file was moved from raw to processed folder."""
    file_key = str(dest_path.resolve())
    processed[file_key] = {
        "filename": dest_path.name,
        "hash": _file_hash(dest_path),
        "origin_path": str(orig_path.resolve()),
        "organized_at": datetime.now().isoformat(),
        "summarized_at": None,
        "drive_doc_id": None,
    }


def mark_summarized(
    file_path: Path, processed: dict, drive_doc_id: str = ""
) -> None:
    """Record that a file was summarized (and optionally uploaded to Drive)."""
    file_key = str(file_path.resolve())
    entry = processed.get(file_key, {})
    entry.update({
        "filename": file_path.name,
        "hash": _file_hash(file_path),
        "summarized_at": datetime.now().isoformat(),
        "drive_doc_id": drive_doc_id or None,
    })
    processed[file_key] = entry


def _file_hash(file_path: Path) -> str:
    try:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except IOError:
        return ""
