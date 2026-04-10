# ============================================================
#  md_writer.py — Genera archivos Markdown para Obsidian
# ============================================================

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def save_summary(
    summary: str,
    source_file: Path,
    subject_name: str,
    obsidian_root: Path,
) -> Path | None:
    """
    Guarda el resumen como archivo .md en la carpeta correcta de Obsidian.
    Retorna la ruta del archivo creado, o None si falló.
    """
    # Crear carpeta de la materia si no existe
    subject_dir = obsidian_root / subject_name
    subject_dir.mkdir(parents=True, exist_ok=True)

    # Nombre del archivo: nombre del doc original + fecha
    date_str = datetime.now().strftime("%Y-%m-%d")
    stem = _sanitize_filename(source_file.stem)
    output_filename = f"{stem}_resumen_{date_str}.md"
    output_path = subject_dir / output_filename

    # Construir el contenido completo del archivo Markdown
    content = _build_markdown(summary, source_file, subject_name)

    try:
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"  ✅ Guardado en: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"  Error al guardar {output_filename}: {e}")
        return None


def _build_markdown(summary: str, source_file: Path, subject_name: str) -> str:
    """
    Construye el archivo Markdown completo con frontmatter de Obsidian.
    El frontmatter permite usar propiedades, búsqueda y dataview en Obsidian.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M")

    frontmatter = f"""---
title: "Resumen: {source_file.stem}"
materia: "{subject_name}"
fecha: {date_str}
fuente: "{source_file.name}"
tipo: resumen-automatico
tags:
  - resumen
  - {_slugify(subject_name)}
  - auto-generado
---

"""

    header = f"# 📚 {source_file.stem}\n\n"
    metadata_line = f"> **Materia:** {subject_name} · **Fuente:** `{source_file.name}` · **Generado:** {datetime_str}\n\n"
    separator = "---\n\n"

    return frontmatter + header + metadata_line + separator + summary + "\n"


def _sanitize_filename(name: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo en Windows."""
    invalid_chars = r'\/:*?"<>|'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name.strip()[:80]  # Máximo 80 caracteres


def _slugify(text: str) -> str:
    """Convierte texto a slug para tags de Obsidian."""
    return (
        text.lower()
        .replace(" ", "-")
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )
