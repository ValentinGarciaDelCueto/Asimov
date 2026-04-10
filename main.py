# ============================================================
#  main.py — Script principal (versión con descarga de campus)
#
#  USO:
#    python main.py                    → descarga + resume archivos nuevos
#    python main.py --skip-download    → solo resume, sin ir al campus
#    python main.py --download-only    → solo descarga, sin resumir
#    python main.py --dry-run          → muestra qué haría, sin API ni campus
#    python main.py --reset            → reprocesa todos los archivos
#    python main.py --subject "Mat"    → solo esa materia
# ============================================================

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from src.extractor import extract_text, count_words
from src.ai_client import summarize_text, estimate_cost
from src.notion_writer import save_to_notion
from src.tracker import load_processed, save_processed, is_processed, mark_as_processed


def setup_logging():
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def discover_files(subject_filter=None):
    """
    Soporta dos estructuras:
    A) Con subcarpetas por materia:
       Materiales facu/Matematicas/archivo.pdf  → materia = "Matematicas"
    B) Todo junto en una carpeta (sin subcarpetas):
       Materiales facu/archivo.pdf              → materia = nombre de la carpeta raiz
    """
    files = []
    root = config.DOCUMENTS_ROOT

    if not root.exists():
        logging.error(f"Carpeta no encontrada: {root}")
        return []

    has_subject_folders = any(
        p.is_dir() and any(
            f.suffix.lower() in config.SUPPORTED_EXTENSIONS
            for f in p.rglob("*")
        )
        for p in root.iterdir()
    )

    if has_subject_folders:
        logging.info("Modo: carpetas por materia detectadas")
        for subject_dir in sorted(root.iterdir()):
            if not subject_dir.is_dir():
                continue
            subject_name = subject_dir.name
            if subject_filter and subject_filter.lower() not in subject_name.lower():
                continue
            for file_path in sorted(subject_dir.rglob("*")):
                if file_path.suffix.lower() in config.SUPPORTED_EXTENSIONS:
                    files.append((file_path, subject_name))
    else:
        subject_name = root.name
        logging.info(f"Modo: archivos sueltos — materia asignada: '{subject_name}'")
        if not subject_filter or subject_filter.lower() in subject_name.lower():
            for file_path in sorted(root.glob("*")):
                if file_path.suffix.lower() in config.SUPPORTED_EXTENSIONS:
                    files.append((file_path, subject_name))

    logging.info(f"Documentos encontrados: {len(files)}")
    return files


def process_file(file_path, subject_name, processed, dry_run=False):
    logger = logging.getLogger(__name__)
    logger.info(f"\n{'─'*50}")
    logger.info(f"📄 {subject_name} / {file_path.name}")

    text = extract_text(file_path)
    if not text:
        logger.warning("  ⚠️  Sin texto extraíble. Saltando.")
        return False

    word_count = count_words(text)
    cost, pdfs_remaining = estimate_cost(word_count)

    if config.PROVIDER == "groq":
        logger.info(f"  Palabras: {word_count:,} | PDFs restantes hoy (aprox): ~{pdfs_remaining}")
    else:
        logger.info(f"  Palabras: {word_count:,} | Costo estimado: ~${cost:.4f} USD")

    if dry_run:
        logger.info("  [DRY RUN] Resumen no generado.")
        return True

    if not config.NOTION_TOKEN or not config.NOTION_DATABASE_ID:
        logger.error(
            "  Credenciales de Notion no configuradas.\n"
            "  Ejecutá en CMD:\n"
            "    set NOTION_TOKEN=secret_xxxxx\n"
            "    set NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        )
        return False

    logger.info(f"  Enviando a {'Groq (llama-3.3-70b)' if config.PROVIDER == 'groq' else 'Claude Haiku'}...")
    summary = summarize_text(text, document_name=file_path.name)

    if not summary:
        logger.error("  ❌ Sin respuesta de la API.")
        return False

    page_id = save_to_notion(
        summary=summary,
        source_file_name=file_path.name,
        subject_name=subject_name,
        database_id=config.NOTION_DATABASE_ID,
        notion_token=config.NOTION_TOKEN,
    )

    if page_id:
        mark_as_processed(file_path, processed, Path(page_id))
        return True

    return False


def run(dry_run=False, subject_filter=None, reset=False,
        skip_download=False, download_only=False):

    logger = logging.getLogger(__name__)
    provider_label = f"Groq ({config.GROQ_MODEL})" if config.PROVIDER == "groq" else f"Anthropic ({config.MODEL})"
    logger.info("=" * 50)
    logger.info("🚀 Academic Summarizer — UNO Campus Edition")
    logger.info(f"   Proveedor: {provider_label}")
    logger.info(f"   Docs:      {config.DOCUMENTS_ROOT}")
    logger.info(f"   Output:    Notion (DB: {config.NOTION_DATABASE_ID or 'no configurado'})")
    logger.info("=" * 50)

    # ── PASO 1: Descargar del campus ─────────────────────────
    if not skip_download and not dry_run:
        logger.info("\n📡 PASO 1: Descargando materiales del campus...")
        try:
            from src.campus_downloader import download_new_materials
            downloaded = download_new_materials(config.DOCUMENTS_ROOT)
            logger.info(f"   {downloaded} archivo(s) nuevo(s) descargados")
        except Exception as e:
            logger.error(f"   Error en descarga del campus: {e}")
            logger.info("   Continuando con archivos locales existentes...")
    elif dry_run:
        logger.info("\n[DRY RUN] Se saltea la descarga del campus")
    else:
        logger.info("\n⏭️  Descarga del campus salteada (--skip-download)")

    if download_only:
        logger.info("\n✅ Modo --download-only finalizado.")
        return

    # ── PASO 2: Procesar y resumir ───────────────────────────
    logger.info("\n🧠 PASO 2: Generando resúmenes con IA...")

    processed = {} if reset else load_processed(config.PROCESSED_LOG)

    all_files = discover_files(subject_filter)
    if not all_files:
        logger.info("No se encontraron documentos.")
        return

    pending = [
        (fp, sn) for fp, sn in all_files
        if not is_processed(fp, processed)
    ]

    logger.info(f"Pendientes: {len(pending)} / {len(all_files)}")

    if not pending:
        logger.info("✅ Todo al día. No hay archivos nuevos para resumir.")
        return

    success_count = 0
    fail_count = 0
    start_time = time.time()

    for i, (file_path, subject_name) in enumerate(pending, 1):
        logger.info(f"\n[{i}/{len(pending)}]")
        success = process_file(file_path, subject_name, processed, dry_run)

        if success:
            success_count += 1
            if not dry_run:
                save_processed(config.PROCESSED_LOG, processed)
        else:
            fail_count += 1

        if i < len(pending) and not dry_run:
            time.sleep(3)

    elapsed = time.time() - start_time
    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Resumidos: {success_count} | ❌ Fallos: {fail_count}")
    logger.info(f"⏱️  Tiempo: {elapsed/60:.1f} min")
    logger.info(f"📋 Resúmenes guardados en Notion")
    logger.info("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resumidor académico — UNO Campus")
    parser.add_argument("--dry-run", action="store_true",
                        help="Sin llamadas a API ni campus")
    parser.add_argument("--reset", action="store_true",
                        help="Reprocesa todos los archivos")
    parser.add_argument("--subject", type=str, default=None,
                        help="Filtra por materia (búsqueda parcial)")
    parser.add_argument("--skip-download", action="store_true",
                        help="Solo resume, sin bajar del campus")
    parser.add_argument("--download-only", action="store_true",
                        help="Solo descarga del campus, sin resumir")

    args = parser.parse_args()
    setup_logging()

    run(
        dry_run=args.dry_run,
        subject_filter=args.subject,
        reset=args.reset,
        skip_download=args.skip_download,
        download_only=args.download_only,
    )
