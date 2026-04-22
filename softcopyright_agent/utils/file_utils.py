"""Filesystem helpers."""

from __future__ import annotations

import re
from pathlib import Path

_WINDOWS_RESERVED = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(name: str, *, fallback: str = "softcopyright") -> str:
    """Create a Windows-safe filename while preserving useful Chinese text."""

    cleaned = _WINDOWS_RESERVED.sub("_", name).strip(" ._")
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80] or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_path(path: str | Path) -> Path:
    """Return a normalized relative path, rejecting traversal and absolute paths."""

    candidate = Path(str(path).replace("\\", "/"))
    if candidate.is_absolute() or candidate.drive:
        raise ValueError(f"unsafe generated path: {path}")

    parts = [part for part in candidate.parts if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"unsafe generated path: {path}")
    return Path(*parts)


def safe_child_path(root: Path, relative_path: str | Path) -> Path:
    """Join a relative path below root and ensure it cannot escape root."""

    safe_relative = safe_relative_path(relative_path)
    root_resolved = root.resolve()
    target = (root_resolved / safe_relative).resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"unsafe generated path: {relative_path}") from exc
    return target
