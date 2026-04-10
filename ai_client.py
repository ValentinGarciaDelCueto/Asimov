# ============================================================
#  ai_client.py — Cliente para la API de Anthropic
# ============================================================

import logging
import time
import anthropic

from config import (
    ANTHROPIC_API_KEY,
    MODEL,
    MAX_TOKENS_RESPONSE,
    SUMMARY_PROMPT_TEMPLATE,
    CHUNK_SIZE,
)
from extractor import split_into_chunks, count_words

logger = logging.getLogger(__name__)


def get_client() -> anthropic.Anthropic:
    """Crea y valida el cliente de Anthropic."""
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY no configurada.\n"
            "Ejecutá en CMD: set ANTHROPIC_API_KEY=sk-ant-tu-key-aqui"
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def summarize_text(text: str, document_name: str = "") -> str:
    """
    Genera un resumen del texto usando Claude.
    Si el texto es muy largo, lo divide en chunks y combina los resúmenes.
    """
    client = get_client()
    word_count = count_words(text)
    logger.info(f"  Texto recibido: {word_count} palabras")

    if word_count <= CHUNK_SIZE:
        # Texto corto: resumen directo
        return _call_api(client, text)
    else:
        # Texto largo: resumir por partes y luego consolidar
        logger.info(f"  Documento largo, dividiendo en chunks...")
        return _summarize_long_document(client, text, document_name)


def _call_api(client: anthropic.Anthropic, text: str, retries: int = 3) -> str:
    """
    Llama a la API con reintentos en caso de error temporal.
    """
    prompt = SUMMARY_PROMPT_TEMPLATE.replace("{text}", text)

    for attempt in range(retries):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS_RESPONSE,
                messages=[{"role": "user", "content": prompt}],
            )
            for block in message.content:
              if block.type == "text":
                return block.text

            return ""

        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            logger.warning(f"  Rate limit alcanzado. Esperando {wait}s...")
            time.sleep(wait)

        except anthropic.APIConnectionError:
            wait = 10 * (attempt + 1)
            logger.warning(f"  Error de conexión. Reintento {attempt + 1}/{retries} en {wait}s...")
            time.sleep(wait)

        except anthropic.APIStatusError as e:
            logger.error(f"  Error de API [{e.status_code}]: {e.message}")
            if e.status_code == 529:  # Overloaded
                time.sleep(60)
            else:
                break

        except Exception as e:
            logger.error(f"  Error inesperado en API: {e}")
            break

    return ""


def _summarize_long_document(
    client: anthropic.Anthropic, text: str, document_name: str
) -> str:
    """
    Estrategia para documentos largos:
    1. Resume cada chunk individualmente
    2. Combina todos los resúmenes parciales en uno final
    """
    chunks = split_into_chunks(text, CHUNK_SIZE)
    partial_summaries = []

    for i, chunk in enumerate(chunks):
        logger.info(f"  Resumiendo chunk {i + 1}/{len(chunks)}...")
        summary = _call_api(client, chunk)
        if summary:
            partial_summaries.append(f"### Parte {i + 1}\n{summary}")
        time.sleep(1)  # Pausa pequeña para no saturar la API

    if not partial_summaries:
        logger.error("  No se generaron resúmenes parciales")
        return ""

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    # Consolidar todos los resúmenes parciales en uno final
    logger.info("  Consolidando resúmenes parciales...")
    combined = "\n\n".join(partial_summaries)
    consolidation_prompt = f"""Tenés los siguientes resúmenes parciales del documento "{document_name}".
Generá UN ÚNICO resumen consolidado y coherente que integre toda la información,
eliminando repeticiones y manteniendo la estructura solicitada.

RESÚMENES PARCIALES:
{combined}

Generá el resumen final con la estructura estándar (Tema Central, Conceptos Clave, Desarrollo, Conexiones, Preguntas para el Examen)."""

    return _call_api(client, consolidation_prompt)


def estimate_cost(word_count: int) -> float:
    """
    Estimación muy aproximada del costo en USD.
    Claude Haiku: ~$0.25 por millón de tokens de input
    1 token ≈ 0.75 palabras
    """
    input_tokens = word_count / 0.75
    cost = (input_tokens / 1_000_000) * 0.25
    return round(cost, 5)
