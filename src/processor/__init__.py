"""Processor — public API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class ProcessReport:
    summarized: list[Path] = field(default_factory=list)
    uploaded: list[str] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)


def process(
    processed_root: Path,
    drive_parent_folder_id: str | None = None,
    subject_filter: str | None = None,
    dry_run: bool = False,
    reset: bool = False,
    on_event: Callable[[str], None] | None = None,
) -> ProcessReport:
    """
    Summarize files in processed_root using AI, upload summaries to Drive.

    - drive_parent_folder_id: Drive folder ID for uploads. None = auto-create "Resumenes UNO".
    - subject_filter: substring match on subject folder name.
    - dry_run: skip API calls and Drive upload.
    - reset: reprocess all files (ignore tracker).
    """
    import config
    from .pipeline import run_pipeline

    def _emit(msg: str) -> None:
        logger.info(msg)
        if on_event:
            on_event(msg)

    drive_client = None
    resolved_folder_id = drive_parent_folder_id or ""

    if not dry_run:
        try:
            from .drive_client import DriveClient
            drive_client = DriveClient.from_oauth(
                config.DRIVE_CREDENTIALS_FILE,
                config.DRIVE_TOKEN_FILE,
            )
            if not resolved_folder_id:
                resolved_folder_id = drive_client.ensure_root_folder()
                _emit(f"Carpeta Drive: {resolved_folder_id}")
        except FileNotFoundError as e:
            _emit(f"Drive no disponible: {e}")
            _emit("Continuando sin subir a Drive...")
        except Exception as e:
            _emit(f"Error conectando a Drive: {e}")
            _emit("Continuando sin subir a Drive...")

    summarized, uploaded, failed = run_pipeline(
        processed_root=processed_root,
        drive_client=drive_client,
        drive_parent_folder_id=resolved_folder_id,
        tracker_log=config.PROCESSED_LOG,
        subject_filter=subject_filter,
        dry_run=dry_run,
        reset=reset,
        on_event=on_event,
    )

    report = ProcessReport(
        summarized=summarized,
        uploaded=uploaded,
        failed=failed,
    )

    _emit(
        f"Proceso completo: {len(summarized)} resumidos, "
        f"{len(uploaded)} subidos a Drive, "
        f"{len(failed)} fallidos"
    )
    return report
