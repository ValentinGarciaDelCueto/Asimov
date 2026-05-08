"""Plan and apply file moves from raw_root to processed_root."""

import logging
import shutil
from pathlib import Path

from .dedup import hash_file
from .rename import normalize_filename

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def plan_moves(
    raw_root: Path,
    processed_root: Path,
) -> list[tuple[Path, Path]]:
    """
    Return list of (src, dst) for files in raw_root that should move to processed_root.
    Skips files whose content hash already exists in processed_root.
    """
    existing_hashes: set[str] = set()
    for f in processed_root.rglob("*"):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            h = hash_file(f)
            if h:
                existing_hashes.add(h)

    moves: list[tuple[Path, Path]] = []
    for src in raw_root.rglob("*"):
        if not src.is_file() or src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        h = hash_file(src)
        if h in existing_hashes:
            logger.debug(f"Duplicate, skip: {src.name}")
            continue

        # Preserve subject subfolder name
        try:
            rel = src.relative_to(raw_root)
            subject_dir = rel.parts[0] if len(rel.parts) > 1 else ""
        except ValueError:
            subject_dir = ""

        safe_name = normalize_filename(src.name)
        dst_dir = processed_root / subject_dir if subject_dir else processed_root
        dst = dst_dir / safe_name

        # Handle name collision
        if dst.exists():
            stem = Path(safe_name).stem
            ext = Path(safe_name).suffix
            counter = 1
            while dst.exists():
                dst = dst_dir / f"{stem}_{counter}{ext}"
                counter += 1

        moves.append((src, dst))

    return moves


def apply_moves(
    moves: list[tuple[Path, Path]],
    dry_run: bool = False,
    on_event=None,
) -> list[tuple[Path, Path]]:
    """Execute planned moves. Returns list of (src, dst) actually moved."""
    done: list[tuple[Path, Path]] = []
    for src, dst in moves:
        msg = f"{'[DRY] ' if dry_run else ''}Mover: {src.name} -> {dst.parent.name}/"
        logger.info(msg)
        if on_event:
            on_event(msg)

        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            done.append((src, dst))
        else:
            done.append((src, dst))

    return done
