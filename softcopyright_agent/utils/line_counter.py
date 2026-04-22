"""Source line counting utilities."""

from __future__ import annotations

from pathlib import Path


def count_text_lines(text: str, *, include_blank: bool = True) -> int:
    """Count lines in a text block."""

    lines = text.splitlines()
    if include_blank:
        return len(lines)
    return sum(1 for line in lines if line.strip())


def count_directory_lines(root: Path, suffixes: tuple[str, ...] = (".py", ".md", ".html", ".css", ".js")) -> int:
    """Count generated source lines below a directory."""

    total = 0
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in suffixes:
            total += count_text_lines(path.read_text(encoding="utf-8"))
    return total
