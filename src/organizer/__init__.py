"""Organizer — public API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .dedup import hash_file
from .move import apply_moves, plan_moves

logger = logging.getLogger(__name__)


@dataclass
class OrganizeReport:
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    duplicates_skipped: list[Path] = field(default_factory=list)
    renamed: list[tuple[str, str]] = field(default_factory=list)


def organize(
    raw_root: Path,
    processed_root: Path,
    dry_run: bool = False,
    on_event: Callable[[str], None] | None = None,
) -> OrganizeReport:
    """
    Move files from raw_root to processed_root.
    - Deduplicates by content hash (skip if already in processed_root)
    - Normalizes filenames (no accents, no illegal chars)
    - Creates subject subfolders automatically
    """

    def _emit(msg: str) -> None:
        logger.info(msg)
        if on_event:
            on_event(msg)

    report = OrganizeReport()
    raw_root.mkdir(parents=True, exist_ok=True)
    processed_root.mkdir(parents=True, exist_ok=True)

    _emit("Planificando movimientos...")
    moves = plan_moves(raw_root, processed_root)

    # Track which were renamed
    for src, dst in moves:
        if src.name != dst.name:
            report.renamed.append((src.name, dst.name))

    done = apply_moves(moves, dry_run=dry_run, on_event=on_event)
    report.moved = done

    _emit(f"Organizado: {len(done)} movidos, {len(report.renamed)} renombrados")
    return report
