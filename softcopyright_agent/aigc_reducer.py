"""Phase 5: text style adjustment for manual review.

Supports both LLM-powered rewriting and deterministic fallback.
"""

from __future__ import annotations

import difflib

from typing import Callable

from .llm import LLMClient, LLMError
from .prompt_engine import PromptEngine


class AIGCReducer:
    """Reduce templated wording and make the document read more like engineering notes.

    This component is a style rewriter. It does not claim to bypass
    or defeat any external AI-content detection system.
    """

    # ── 确定性替换词典（扩充至 30+ 条常见 AI 套话）──────────────────────
    REPLACEMENTS: dict[str, str] = {
        # 删除类（AI 高频废话，直接删除）
        "值得注意的是，": "",
        "值得注意的是": "",
        "需要指出的是，": "",
        "需要指出的是": "",
        "需要强调的是，": "",
        "需要强调的是": "",
        "不可忽视的是，": "",
        "不可忽视的是": "",
        "众所周知，": "",
        "众所周知": "",
        "毋庸置疑，": "",
        "毋庸置疑": "",
        "显而易见，": "",
        "显而易见": "",
        "不言而喻，": "",
        "不言而喻": "",
        # 总结类套话替换
        "总的来说": "从工程落地角度看",
        "总而言之": "回到工程实践",
        "综上所述": "按上述设计",
        "综上": "按上述设计",
        "总结来看": "梳理下来",
        # 动词替换（降低工整感）
        "实现了": "完成了",
        "实现": "完成",
        "采用了": "选用了",
        "采用": "选用",
        "利用了": "借助",
        "利用": "借助",
        "能够": "可以",
        "确保": "保证",
        "旨在": "目的是",
        "致力于": "着重做",
        "有效地": "较好地",
        "显著地": "明显",
        "极大地": "大幅",
        # 连接词替换（打破 AI 排比节奏）
        "此外，": "另外，",
        "与此同时，": "同时，",
        "在此基础上，": "基于这个思路，",
        "具体而言，": "展开来看，",
        "更为重要的是，": "关键在于，",
        "进一步地，": "再往前一步，",
        "在该模块中，": "这个模块里，",
        # 句式软化
        "提供了强大的": "提供了",
        "高效的": "可用的",
        "全面的": "较完整的",
        "完善的": "基本完备的",
        "灵活的": "可调整的",
        "可扩展的": "留有扩展余地的",
        "健壮的": "经过加固的",
    }

    # ── 句式级别的上下文替换 ───────────────────────────────────────
    CONTEXT_REPLACEMENTS: list[tuple[str, str]] = [
        ("。系统", "。在本系统中，"),
        ("。设计时", "。落到设计细节时"),
        ("。该模块", "。这一模块"),
        ("，从而实现", "，这样就能做到"),
        ("，以满足", "，来满足"),
        ("，进而", "，然后"),
    ]

    def reduce_document(
        self,
        chapters: dict[str, str],
        *,
        llm_client: LLMClient | None = None,
        prompt_engine: PromptEngine | None = None,
        rounds: int = 1,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> dict[str, str]:
        """Reduce AIGC traces from all chapters."""
        result: dict[str, str] = {}
        total_chapters = len(chapters)
        for i, (chapter_id, text) in enumerate(chapters.items()):
            if progress_callback:
                progress_callback("说明书降重", 0.6 + 0.2 * (i / max(total_chapters, 1)), f"正在改写章节 {chapter_id} ({i+1}/{total_chapters})")
            reduced = text
            if llm_client is not None:
                reduced = self._reduce_with_llm(
                    chapter_id, reduced, llm_client, prompt_engine or PromptEngine(), rounds
                )
            else:
                reduced = self.reduce_text(reduced)
            result[chapter_id] = reduced
        return result

    def reduce_text(self, text: str) -> str:
        """Apply deterministic replacements (fallback mode)."""
        rewritten = text
        for source, target in self.REPLACEMENTS.items():
            rewritten = rewritten.replace(source, target)
        for source, target in self.CONTEXT_REPLACEMENTS:
            rewritten = rewritten.replace(source, target)
        return rewritten

    def _reduce_with_llm(
        self,
        chapter_id: str,
        text: str,
        llm_client: LLMClient,
        prompt_engine: PromptEngine,
        rounds: int,
    ) -> str:
        """Call LLM to rewrite a chapter, with optional multi-round passes."""
        current = text
        for round_index in range(max(1, rounds)):
            try:
                prompt = prompt_engine.render(
                    "reduce_aigc.md",
                    original_text=current,
                    round_number=round_index + 1,
                    total_rounds=rounds,
                    chapter_id=chapter_id,
                )
                rewritten = llm_client.generate(
                    system=(
                        "你是一位资深技术文档编辑。你的任务是改写软件设计说明书段落，"
                        "使其读起来像工程师手写的技术文档而不是 AI 生成的内容。"
                        "严格保持技术内容准确，保持字数基本不变，只输出改写后的文本。"
                    ),
                    user=prompt,
                    temperature=0.55,
                )
                rewritten = rewritten.strip()
                if rewritten and len(rewritten) > len(current) * 0.5:
                    current = rewritten + "\n"
                else:
                    # LLM 返回了明显不合理的结果，回退到确定性替换
                    current = self.reduce_text(current)
                    break
            except LLMError:
                # LLM 调用失败，回退到确定性替换
                current = self.reduce_text(current)
                break
        return current

    @staticmethod
    def assess_reduction(original: str, reduced: str) -> dict[str, float]:
        """Compute simple metrics comparing original vs reduced text.

        Returns a dict with:
            - change_ratio: fraction of lines changed (0.0 ~ 1.0)
            - length_ratio: reduced length / original length
        """
        orig_lines = original.splitlines()
        redu_lines = reduced.splitlines()
        matcher = difflib.SequenceMatcher(None, orig_lines, redu_lines)
        unchanged = sum(block.size for block in matcher.get_matching_blocks())
        total = max(len(orig_lines), 1)
        change_ratio = 1.0 - unchanged / total
        length_ratio = len(reduced) / max(len(original), 1)
        return {"change_ratio": round(change_ratio, 3), "length_ratio": round(length_ratio, 3)}
