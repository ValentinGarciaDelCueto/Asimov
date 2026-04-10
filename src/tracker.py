# ============================================================
#  src/tracker.py — Registro de archivos ya procesados
#  Evita resumir el mismo documento dos veces
# ============================================================

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def load_processed(log_path: Path) -> dict:
    """Carga el registro de archivos procesados desde JSON."""
    if not log_path.exists():
        return {}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"No se pudo cargar el registro: {e}. Iniciando vacío.")
        return {}


def save_processed(log_path: Path, processed: dict) -> None:
    """Guarda el registro actualizado."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"No se pudo guardar el registro: {e}")


def is_processed(file_path: Path, processed: dict) -> bool:
    """
    Verifica si un archivo ya fue procesado.
    Usa el hash MD5 del archivo para detectar si cambió el contenido
    (así re-procesa si el archivo fue modificado).
    """
    file_key = str(file_path.resolve())
    if file_key not in processed:
        return False

    # Verificar si el archivo cambió desde la última vez
    current_hash = _file_hash(file_path)
    stored_hash = processed[file_key].get("hash", "")

    if current_hash != stored_hash:
        logger.info(f"  Archivo modificado, se volverá a procesar: {file_path.name}")
        return False

    return True


def mark_as_processed(
    file_path: Path, processed: dict, output_path: Path | None = None
) -> None:
    """Registra un archivo como procesado con su hash y metadata."""
    file_key = str(file_path.resolve())
    processed[file_key] = {
        "filename": file_path.name,
        "hash": _file_hash(file_path),
        "processed_at": datetime.now().isoformat(),
        "output": str(output_path) if output_path else None,
    }


def _file_hash(file_path: Path) -> str:
    """Calcula el hash MD5 de un archivo para detectar cambios."""
    try:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except IOError:
        return ""
