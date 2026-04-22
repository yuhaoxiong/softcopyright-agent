"""Chapter quality self-checker — the core of Agent Phase A.

Performs deterministic quality assessment against CPCC spec requirements
without any LLM calls, enabling instant feedback for the self-check
retry loop in the agent orchestrator.
"""

from __future__ import annotations

import re

from ..models import Chapter
from ..utils.word_counter import count_words
from .base import ToolResult

# ── Per-chapter CPCC requirements ────────────────────────────────

_DIAGRAM_RULES: dict[str, dict] = {
    "chapter_1": {"min_diagrams": 0, "requires_table": False},
    "chapter_2": {"min_diagrams": 2, "requires_table": False},
    "chapter_3": {"min_diagrams": 1, "requires_table": False},
    "chapter_4": {"min_diagrams": 2, "requires_table": False},
    "chapter_5": {"min_diagrams": 1, "requires_table": True},
    "chapter_6": {"min_diagrams": 1, "requires_table": True},
    "chapter_7": {"min_diagrams": 1, "requires_table": False},
}

# Phrases that betray AI-generated text or violate CPCC purity
_FORBIDDEN_PHRASES = [
    "值得注意的是", "需要指出的是", "总的来说", "综上所述",
    "众所周知", "不言而喻", "毋庸置疑", "显而易见",
    "如下是", "好的，", "以下是按照", "撰写提示",
    "注意事项", "未来展望", "下一步计划",
]

_DIAGRAM_NUMBERING_RE = re.compile(r"\*\*图\d+-\d+")
_TABLE_ROW_RE = re.compile(r"^\|.+\|.+\|", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{2,3}\s+\S", re.MULTILINE)


class ChapterQualityChecker:
    """Deterministic quality assessor for individual chapters.

    Scoring breakdown (100 points total):
        - Word count vs target:    0-25
        - Mermaid diagram count:   0-25
        - Diagram numbering:       0-15
        - Table presence:          0-15
        - Section structure:       0-10
        - Forbidden phrase scan:   0-10
    """

    def check(self, chapter_id: str, content: str, chapter: Chapter) -> ToolResult:
        """Assess a single chapter and return a structured quality report."""
        issues: list[str] = []
        scores: dict[str, int] = {}

        rule = _DIAGRAM_RULES.get(chapter_id, {"min_diagrams": 0, "requires_table": False})

        scores["word_count"] = self._check_word_count(content, chapter.target_words, issues)
        scores["diagrams"] = self._check_diagrams(content, rule["min_diagrams"], issues)
        scores["diagram_numbering"] = self._check_diagram_numbering(content, issues)
        scores["tables"] = self._check_tables(content, rule.get("requires_table", False), issues)
        scores["sections"] = self._check_sections(content, chapter.sections, issues)
        scores["purity"] = self._check_forbidden_phrases(content, issues)

        total = sum(scores.values())

        parts = [f"章节 {chapter_id} 质量评分: {total}/100"]
        if issues:
            parts.append("问题:")
            for issue in issues:
                parts.append(f"  - {issue}")
        else:
            parts.append("所有检查项通过。")

        return ToolResult(
            success=total >= 70,
            data={"score": total, "issues": issues, "breakdown": scores},
            observation="\n".join(parts),
            metrics={"quality_score": float(total)},
        )

    # ── Individual check dimensions ──────────────────────────────

    def _check_word_count(self, content: str, target: int, issues: list[str]) -> int:
        actual = count_words(content)
        ratio = actual / max(target, 1)
        if ratio >= 0.85:
            return 25
        if ratio >= 0.65:
            issues.append(f"字数偏少: {actual}/{target} ({ratio:.0%})")
            return 15
        if ratio >= 0.45:
            issues.append(f"字数严重不足: {actual}/{target} ({ratio:.0%})")
            return 8
        issues.append(f"字数极度不足: {actual}/{target} ({ratio:.0%})")
        return 0

    def _check_diagrams(self, content: str, min_required: int, issues: list[str]) -> int:
        if min_required == 0:
            return 25
        mermaid_count = content.count("```mermaid")
        if mermaid_count >= min_required:
            return 25
        if mermaid_count > 0:
            issues.append(f"Mermaid 图表不足: 有 {mermaid_count} 张, 要求至少 {min_required} 张")
            return 15
        issues.append(f"缺少 Mermaid 图表: 要求至少 {min_required} 张")
        return 0

    def _check_diagram_numbering(self, content: str, issues: list[str]) -> int:
        mermaid_count = content.count("```mermaid")
        if mermaid_count == 0:
            return 15  # no diagrams to number
        numbering_count = len(_DIAGRAM_NUMBERING_RE.findall(content))
        if numbering_count >= mermaid_count:
            return 15
        if numbering_count > 0:
            issues.append(f"部分图表缺少编号: {numbering_count}/{mermaid_count} 有 **图X-Y** 编号")
            return 8
        issues.append("所有图表均缺少 **图X-Y 标题** 编号")
        return 0

    def _check_tables(self, content: str, requires_table: bool, issues: list[str]) -> int:
        if not requires_table:
            return 15
        if _TABLE_ROW_RE.search(content):
            return 15
        issues.append("该章节需要数据表格但未找到 Markdown 表格")
        return 0

    def _check_sections(self, content: str, expected_sections: list[str], issues: list[str]) -> int:
        expected = len(expected_sections)
        if expected == 0:
            return 10
        heading_count = len(_HEADING_RE.findall(content))
        if heading_count / max(expected, 1) >= 0.7:
            return 10
        if heading_count > 0:
            issues.append(f"子节不足: 有 {heading_count} 节, 期望约 {expected} 节")
            return 5
        issues.append(f"缺少子节标题: 期望约 {expected} 个 ##/### 级标题")
        return 0

    def _check_forbidden_phrases(self, content: str, issues: list[str]) -> int:
        found = [p for p in _FORBIDDEN_PHRASES if p in content]
        if not found:
            return 10
        preview = ", ".join(found[:3])
        suffix = f" 等共 {len(found)} 个" if len(found) > 3 else ""
        issues.append(f"包含应避免的短语: {preview}{suffix}")
        return 5 if len(found) <= 2 else 0
