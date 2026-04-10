# ============================================================
#  notion_writer.py — Guarda resúmenes en Notion
#
#  Endpoints usados:
#    - databases.query()          → verificar duplicados
#    - pages.create()             → crear la página con el resumen
#    - blocks.children.append()   → agregar bloques si el resumen es largo
# ============================================================

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Límite de Notion: 2000 caracteres por bloque de rich_text
BLOCK_CHAR_LIMIT = 2000


def save_to_notion(
    summary: str,
    source_file_name: str,
    subject_name: str,
    database_id: str,
    notion_token: str,
) -> "str | None":
    """
    Guarda el resumen en Notion como una nueva página en la base de datos.

    Flujo:
      1. databases.query()          → ¿ya existe una página con este nombre?
      2. pages.create()             → crea la página con propiedades + primeros bloques
      3. blocks.children.append()   → agrega el resto si el resumen es largo

    Retorna el page_id de la página creada, o None si falló o ya existía.
    """
    try:
        from notion_client import Client
    except ImportError:
        logger.error(
            "notion-client no instalado.\n"
            "Ejecutá: pip install notion-client"
        )
        return None

    notion = Client(auth=notion_token)

    # 1. Verificar duplicado
    if _already_exists(notion, database_id, source_file_name):
        logger.info(f"  ⏭️  Ya existe en Notion: {source_file_name}")
        return None

    # 2. Convertir markdown a bloques de Notion
    blocks = _markdown_to_blocks(summary)

    # pages.create acepta máximo 100 children de una vez
    first_batch = blocks[:100]
    remaining = blocks[100:]

    date_str = datetime.now().strftime("%Y-%m-%d")

    try:
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Nombre": {
                    "title": [{"text": {"content": source_file_name}}]
                },
                "Materia": {
                    "rich_text": [{"text": {"content": subject_name}}]
                },
                "Fecha": {
                    "date": {"start": date_str}
                },
                "Estado": {
                    "select": {"name": "Pendiente"}
                },
            },
            children=first_batch,
        )
        page_id = response["id"] # type: ignore
        logger.info(f"  ✅ Página creada en Notion: {source_file_name}")

        # 3. Agregar bloques restantes si los hay
        if remaining:
            _append_in_batches(notion, page_id, remaining)

        return page_id

    except Exception as e:
        logger.error(f"  Error al crear página en Notion: {e}")
        return None


# ── Helpers internos ─────────────────────────────────────────

def _already_exists(notion, database_id: str, file_name: str) -> bool:
    """
    Consulta la base de datos para verificar si ya existe una página
    con ese nombre de archivo (propiedad "Nombre").
    """
    try:
        result = notion.databases.query(
            database_id=database_id,
            filter={"property": "Nombre", "title": {"equals": file_name}}
        )
        return len(result["results"]) > 0
    except Exception as e:
        logger.warning(f"  No se pudo verificar duplicados en Notion: {e}")
        return False


def _append_in_batches(notion, page_id: str, blocks: list) -> None:
    """Agrega bloques extra en lotes de 100 (límite de la API de Notion)."""
    for i in range(0, len(blocks), 100):
        batch = blocks[i:i + 100]
        try:
            notion.blocks.children.append(block_id=page_id, children=batch)
        except Exception as e:
            logger.error(f"  Error al agregar bloques extras a Notion: {e}")
            break


# ── Conversión Markdown → bloques Notion ─────────────────────

def _markdown_to_blocks(text: str) -> list:
    """
    Convierte el markdown del resumen a bloques de Notion.
    Reconoce: ## encabezados, # encabezados, - listas, 1. listas numeradas,
    y párrafos normales. Respeta el límite de 2000 chars por bloque.
    """
    blocks = []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        if line.startswith("## "):
            blocks.extend(_make_blocks("heading_2", line[3:]))
        elif line.startswith("# "):
            blocks.extend(_make_blocks("heading_1", line[2:]))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.extend(_make_blocks("bulleted_list_item", line[2:]))
        elif len(line) > 2 and line[0].isdigit() and ". " in line[:5]:
            idx = line.index(". ") + 2
            blocks.extend(_make_blocks("numbered_list_item", line[idx:]))
        else:
            blocks.extend(_make_blocks("paragraph", line))

    return blocks


def _make_blocks(block_type: str, text: str) -> list:
    """
    Crea uno o más bloques del tipo dado, dividiendo el texto
    en chunks de BLOCK_CHAR_LIMIT si es necesario.
    """
    if not text:
        return []
    chunks = [text[i:i + BLOCK_CHAR_LIMIT] for i in range(0, len(text), BLOCK_CHAR_LIMIT)]
    return [
        {
            "object": "block",
            "type": block_type,
            block_type: {"rich_text": [{"text": {"content": chunk}}]},
        }
        for chunk in chunks
    ]
