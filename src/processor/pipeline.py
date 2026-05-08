"""Extract → summarize → upload to Drive → update tracker."""

import logging
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def run_pipeline(
    processed_root: Path,
    drive_client,
    drive_parent_folder_id: str,
    tracker_log: Path,
    subject_filter: str | None = None,
    dry_run: bool = False,
    reset: bool = False,
    on_event: Callable[[str], None] | None = None,
) -> tuple[list[Path], list[str], list[tuple[Path, str]]]:
    """
    Iterate processed_root, summarize each pending file, upload to Drive.

    Returns: (summarized_files, uploaded_drive_ids, failed_list)
    """
    from src.tracker import (
        load_processed, save_processed,
        is_processed, mark_summarized,
    )
    from .summarize import summarize_file

    def _emit(msg: str) -> None:
        logger.info(msg)
        if on_event:
            on_event(msg)

    processed = {} if reset else load_processed(tracker_log)

    all_files: list[tuple[Path, str]] = []
    for subject_dir in sorted(processed_root.iterdir()):
        if not subject_dir.is_dir():
            continue
        subject_name = subject_dir.name
        if subject_filter and subject_filter.lower() not in subject_name.lower():
            continue
        for f in sorted(subject_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                all_files.append((f, subject_name))

    # Also handle files directly in processed_root (no subject subfolder)
    for f in processed_root.glob("*"):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            all_files.append((f, processed_root.name))

    pending = [(fp, sn) for fp, sn in all_files if not is_processed(fp, processed)]
    _emit(f"Pendientes: {len(pending)} / {len(all_files)}")

    summarized: list[Path] = []
    uploaded: list[str] = []
    failed: list[tuple[Path, str]] = []

    for i, (file_path, subject_name) in enumerate(pending, 1):
        _emit(f"[{i}/{len(pending)}] {subject_name} / {file_path.name}")

        if dry_run:
            _emit("  [DRY RUN] Resumen no generado.")
            summarized.append(file_path)
            continue

        try:
            summary = summarize_file(file_path)
            if not summary:
                failed.append((file_path, "Sin resumen generado"))
                continue

            drive_id = ""
            if drive_client and drive_parent_folder_id:
                subject_folder_id = drive_client.ensure_subject_folder(
                    drive_parent_folder_id, subject_name
                )
                doc_name = file_path.stem
                drive_id = drive_client.upload_markdown_as_doc(
                    summary, doc_name, subject_folder_id
                )
                uploaded.append(drive_id)
            else:
                _emit("  Drive no configurado, resumen no subido.")

            mark_summarized(file_path, processed, drive_id)
            save_processed(tracker_log, processed)
            summarized.append(file_path)

        except Exception as e:
            err_msg = f"Error procesando {file_path.name}: {e}"
            logger.error(err_msg)
            failed.append((file_path, str(e)))

        if i < len(pending) and not dry_run:
            time.sleep(2)

    return summarized, uploaded, failed
