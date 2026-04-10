# ============================================================
#  src/ai_client.py — Cliente de IA (Groq o Anthropic)
#
#  Proveedor activo: config.PROVIDER
#    "groq"      → llama-3.3-70b-versatile (free tier)
#    "anthropic" → Claude Haiku (pago)
# ============================================================

import logging
import time

from config import (
    ANTHROPIC_API_KEY, MODEL,
    GROQ_API_KEY, GROQ_MODEL, GROQ_CHUNK_SIZE, GROQ_DAILY_LIMIT,
    PROVIDER, MAX_TOKENS_RESPONSE, SUMMARY_PROMPT_TEMPLATE, CHUNK_SIZE,
)
from src.extractor import split_into_chunks, count_words

logger = logging.getLogger(__name__)


# ── Punto de entrada público ─────────────────────────────────

def summarize_text(text: str, document_name: str = "") -> str:
    """
    Genera un resumen del texto usando el proveedor configurado.
    Si el texto es muy largo, lo divide en chunks y combina los resúmenes.
    """
    if PROVIDER == "groq":
        return _summarize_with_groq(text, document_name)
    return _summarize_with_anthropic(text, document_name)


def estimate_cost(word_count: int) -> tuple[float, int]:
    """
    Retorna (costo_usd, pdfs_restantes_groq).
    - Con Anthropic: costo_usd estimado, pdfs_restantes = 0
    - Con Groq:      costo_usd = 0.0, pdfs_restantes estimado del límite diario
    """
    tokens = int(word_count / 0.75)
    if PROVIDER == "groq":
        pdfs_remaining = GROQ_DAILY_LIMIT // max(tokens, 1)
        return 0.0, pdfs_remaining
    cost = (tokens / 1_000_000) * 0.25  # Haiku: ~$0.25/M tokens input
    return round(cost, 5), 0


# ── Groq ─────────────────────────────────────────────────────

def _summarize_with_groq(text: str, document_name: str) -> str:
    if not GROQ_API_KEY:
        logger.error(
            "GROQ_API_KEY no configurada.\n"
            "Ejecutá en CMD: set GROQ_API_KEY=gsk_tu-key-aqui"
        )
        return ""

    word_count = count_words(text)
    logger.info(f"  Texto recibido: {word_count} palabras")

    if word_count <= GROQ_CHUNK_SIZE:
        return _call_groq_api(SUMMARY_PROMPT_TEMPLATE.replace("{text}", text))

    logger.info("  Documento largo, dividiendo en chunks...")
    chunks = split_into_chunks(text, GROQ_CHUNK_SIZE)
    partial_summaries = []

    for i, chunk in enumerate(chunks):
        logger.info(f"  Resumiendo chunk {i + 1}/{len(chunks)}...")
        summary = _call_groq_api(SUMMARY_PROMPT_TEMPLATE.replace("{text}", chunk))
        if summary:
            partial_summaries.append(f"### Parte {i + 1}\n{summary}")
        time.sleep(3)  # Respetar límite de 6000 tok/min de Groq

    if not partial_summaries:
        logger.error("  No se generaron resúmenes parciales")
        return ""

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    logger.info("  Consolidando resúmenes parciales...")
    combined = "\n\n".join(partial_summaries)
    consolidation_prompt = (
        f'Tenés los siguientes resúmenes parciales del documento "{document_name}".\n'
        "Generá UN ÚNICO resumen consolidado y coherente que integre toda la información,\n"
        "eliminando repeticiones y manteniendo la estructura solicitada.\n\n"
        f"RESÚMENES PARCIALES:\n{combined}\n\n"
        "Generá el resumen final con la estructura estándar "
        "(Tema Central, Conceptos Clave, Desarrollo, Conexiones, Preguntas para el Examen)."
    )
    return _call_groq_api(consolidation_prompt)


def _call_groq_api(prompt: str, retries: int = 3) -> str:
    try:
        from groq import Groq, RateLimitError, APIConnectionError
    except ImportError:
        logger.error(
            "groq no instalado.\n"
            "Ejecutá: pip install groq"
        )
        return ""

    client = Groq(api_key=GROQ_API_KEY)

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS_RESPONSE,
            )
            return response.choices[0].message.content or ""

        except RateLimitError:
            wait = 60
            logger.warning(f"  Rate limit de Groq. Esperando {wait}s... (intento {attempt + 1}/{retries})")
            time.sleep(wait)

        except APIConnectionError:
            wait = 10 * (attempt + 1)
            logger.warning(f"  Error de conexión Groq. Reintento {attempt + 1}/{retries} en {wait}s...")
            time.sleep(wait)

        except Exception as e:
            logger.error(f"  Error inesperado en Groq API: {e}")
            break

    return ""


# ── Anthropic ────────────────────────────────────────────────

def _summarize_with_anthropic(text: str, document_name: str) -> str:
    try:
        import anthropic
    except ImportError:
        logger.error(
            "anthropic no instalado.\n"
            "Ejecutá: pip install anthropic"
        )
        return ""

    if not ANTHROPIC_API_KEY:
        logger.error(
            "ANTHROPIC_API_KEY no configurada.\n"
            "Ejecutá en CMD: set ANTHROPIC_API_KEY=sk-ant-tu-key-aqui"
        )
        return ""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    word_count = count_words(text)
    logger.info(f"  Texto recibido: {word_count} palabras")

    if word_count <= CHUNK_SIZE:
        return _call_anthropic_api(client, text)

    logger.info("  Documento largo, dividiendo en chunks...")
    chunks = split_into_chunks(text, CHUNK_SIZE)
    partial_summaries = []

    for i, chunk in enumerate(chunks):
        logger.info(f"  Resumiendo chunk {i + 1}/{len(chunks)}...")
        summary = _call_anthropic_api(client, chunk)
        if summary:
            partial_summaries.append(f"### Parte {i + 1}\n{summary}")
        time.sleep(1)

    if not partial_summaries:
        logger.error("  No se generaron resúmenes parciales")
        return ""

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    logger.info("  Consolidando resúmenes parciales...")
    combined = "\n\n".join(partial_summaries)
    consolidation_prompt = (
        f'Tenés los siguientes resúmenes parciales del documento "{document_name}".\n'
        "Generá UN ÚNICO resumen consolidado y coherente que integre toda la información,\n"
        "eliminando repeticiones y manteniendo la estructura solicitada.\n\n"
        f"RESÚMENES PARCIALES:\n{combined}\n\n"
        "Generá el resumen final con la estructura estándar "
        "(Tema Central, Conceptos Clave, Desarrollo, Conexiones, Preguntas para el Examen)."
    )
    return _call_anthropic_api(client, consolidation_prompt)


def _call_anthropic_api(client, text: str, retries: int = 3) -> str:
    import anthropic

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
            if e.status_code == 529:
                time.sleep(60)
            else:
                break

        except Exception as e:
            logger.error(f"  Error inesperado en Anthropic API: {e}")
            break

    return ""
