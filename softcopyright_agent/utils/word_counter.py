"""Word and Chinese character counting utilities."""

from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z0-9_+#.-]+")


def count_words(text: str) -> int:
    """Count Chinese characters and Latin tokens as a practical document budget."""

    cjk_count = len(_CJK_RE.findall(text))
    without_cjk = _CJK_RE.sub(" ", text)
    latin_count = len(_LATIN_TOKEN_RE.findall(without_cjk))
    return cjk_count + latin_count


def summarize_word_counts(chapters: dict[str, str]) -> dict[str, int]:
    """Return per-chapter counts plus a total entry."""

    counts = {chapter_id: count_words(content) for chapter_id, content in chapters.items()}
    counts["total"] = sum(counts.values())
    return counts
