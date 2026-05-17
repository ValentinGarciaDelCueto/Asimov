# ============================================================
#  main.py — Dispatcher principal
#
#  USO:
#    python main.py                     → descargar + organizar + resumir
#    python main.py --download-only     → solo descarga del campus
#    python main.py --skip-download     → organizar + resumir (sin campus)
#    python main.py --dry-run           → sin API ni campus
#    python main.py --reset             → reprocesar todos los archivos
#    python main.py --subject "POO II"  → filtrar por materia
#    python tui.py                      → interfaz gráfica
# ============================================================

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config


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


def run(
    dry_run: bool = False,
    subject_filter: str | None = None,
    reset: bool = False,
    skip_download: bool = False,
    download_only: bool = False,
    year: int | None = None,
    headless: bool | None = None,
):
    logger = logging.getLogger(__name__)
    provider_label = (
        f"Groq ({config.GROQ_MODEL})" if config.PROVIDER == "groq"
        else f"Anthropic ({config.MODEL})"
    )
    logger.info("=" * 50)
    logger.info("Asimov — UNO Campus Edition")
    logger.info(f"   Proveedor: {provider_label}")
    logger.info(f"   Raw:       {config.RAW_ROOT}")
    logger.info(f"   Procesado: {config.PROCESSED_ROOT}")
    logger.info("=" * 50)

    # ── PASO 1: Descargar del campus ─────────────────────────
    if not skip_download and not dry_run:
        logger.info("\nPASO 1: Descargando materiales del campus...")
        try:
            from src.downloader import download
            effective_headless = config.CAMPUS_HEADLESS if headless is None else headless
            report = download(
                raw_root=config.RAW_ROOT,
                subject_filter=subject_filter,
                year=year,
                headless=effective_headless,
            )
            logger.info(
                f"   {len(report.files_downloaded)} nuevo(s), "
                f"{len(report.files_skipped)} existente(s), "
                f"{len(report.errors)} error(es)"
            )
        except Exception as e:
            logger.error(f"Error en descarga del campus: {e}")
            logger.info("Continuando con archivos locales existentes...")
    elif dry_run:
        logger.info("\n[DRY RUN] Descarga del campus salteada")
    else:
        logger.info("\nDescarga salteada (--skip-download)")

    if download_only:
        logger.info("\nModo --download-only finalizado.")
        return

    # ── PASO 2: Organizar raw → processed ───────────────────
    logger.info("\nPASO 2: Organizando archivos...")
    try:
        from src.organizer import organize
        org_report = organize(
            raw_root=config.RAW_ROOT,
            processed_root=config.PROCESSED_ROOT,
            dry_run=dry_run,
        )
        logger.info(
            f"   {len(org_report.moved)} movido(s), "
            f"{len(org_report.renamed)} renombrado(s)"
        )
    except Exception as e:
        logger.error(f"Error en organización: {e}")

    # ── PASO 3: Resumir y subir a Drive ─────────────────────
    logger.info("\nPASO 3: Generando resúmenes con IA...")
    try:
        from src.processor import process
        proc_report = process(
            processed_root=config.PROCESSED_ROOT,
            drive_parent_folder_id=config.DRIVE_PARENT_FOLDER_ID or None,
            subject_filter=subject_filter,
            dry_run=dry_run,
            reset=reset,
        )
        logger.info(
            f"   {len(proc_report.summarized)} resumido(s), "
            f"{len(proc_report.uploaded)} subido(s) a Drive, "
            f"{len(proc_report.failed)} fallido(s)"
        )
    except Exception as e:
        logger.error(f"Error en procesamiento: {e}")

    logger.info("=" * 50)
    logger.info("Completado.")
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
                        help="Solo organiza y resume, sin bajar del campus")
    parser.add_argument("--download-only", action="store_true",
                        help="Solo descarga del campus")
    parser.add_argument("--year", type=int, default=None,
                        help="Filtra cursos por año (ej: 2026)")

    args = parser.parse_args()
    setup_logging()

    run(
        dry_run=args.dry_run,
        subject_filter=args.subject,
        reset=args.reset,
        skip_download=args.skip_download,
        download_only=args.download_only,
        year=args.year,
    )
