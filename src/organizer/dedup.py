"""Deduplication via MD5 hash."""

import hashlib
from pathlib import Path


def hash_file(path: Path) -> str:
    """Return MD5 hex digest of file content."""
    md5 = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except IOError:
        return ""


def find_duplicates(root: Path) -> dict[str, list[Path]]:
    """Return {hash: [path1, path2, ...]} for files with the same content."""
    seen: dict[str, list[Path]] = {}
    for p in root.rglob("*"):
        if p.is_file():
            h = hash_file(p)
            if h:
                seen.setdefault(h, []).append(p)
    return {h: paths for h, paths in seen.items() if len(paths) > 1}
