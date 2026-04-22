"""Phase 3: design document writing."""

from __future__ import annotations

import json

from typing import Callable

from .llm import LLMClient
from .models import AnalysisResult, Chapter, Outline
from .prompt_engine import PromptEngine
from .utils.word_counter import count_words


class DocumentWriter:
    """Create a structured Chinese design document from analysis and outline."""

    def write(
        self,
        analysis: AnalysisResult,
        outline: Outline,
        *,
        llm_client: LLMClient | None = None,
        prompt_engine: PromptEngine | None = None,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> dict[str, str]:
        chapters: dict[str, str] = {}
        previous_summary = ""
        total_chapters = len(outline.chapters)
        for i, chapter in enumerate(outline.chapters):
            if progress_callback:
                progress_callback("说明书编写", 0.4 + 0.2 * (i / max(total_chapters, 1)), f"正在编写：{chapter.title} ({i+1}/{total_chapters})")
            content = self.write_chapter(
                chapter,
                analysis,
                previous_summary,
                outline=outline,
                llm_client=llm_client,
                prompt_engine=prompt_engine,
                progress_callback=progress_callback,
            )
            chapters[chapter.id] = content
            previous_summary = (previous_summary + "\n" + self._summarize(content))[-1200:]
        return chapters

    def write_chapter(
        self,
        chapter: Chapter,
        analysis: AnalysisResult,
        previous_summary: str = "",
        *,
        outline: Outline | None = None,
        llm_client: LLMClient | None = None,
        prompt_engine: PromptEngine | None = None,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> str:
        if llm_client is not None and outline is not None:
            prompt_engine = prompt_engine or PromptEngine()
            prompt = prompt_engine.render(
                "write_chapter.md",
                title=analysis.title,
                chapter_title=chapter.title,
                target_words=chapter.target_words,
                title_analysis=json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
                outline=json.dumps(outline.to_dict(), ensure_ascii=False, indent=2),
                previous_chapters_summary=previous_summary,
            )
            return llm_client.generate(
                system="你是资深软件架构师，专门编写可读性强、细节充分的软件著作权设计说明书。",
                user=prompt,
                temperature=0.45,
            ).strip() + "\n"
        return self._fallback_write_chapter(chapter, analysis, previous_summary)

    def _fallback_write_chapter(self, chapter: Chapter, analysis: AnalysisResult, previous_summary: str = "") -> str:
        lines = [f"# {chapter.title}", ""]
        section_budget = max(30, chapter.target_words // max(1, len(chapter.sections)))
        for section in chapter.sections:
            lines.extend([f"## {section}", ""])
            lines.append(self._section_paragraph(section, analysis, previous_summary, section_budget))
            lines.append("")
            if chapter.id == "chapter_3" and section.endswith("功能设计"):
                lines.extend(self._module_function_table(analysis))
            if chapter.id == "chapter_4" and "数据表" in section:
                lines.extend(self._database_table(analysis))
            if chapter.id == "chapter_5" and "接口" in section:
                lines.extend(self._interface_table(analysis))

        while count_words("\n".join(lines)) < int(chapter.target_words * 0.62):
            lines.append(self._expansion_paragraph(chapter, analysis, len(lines)))
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def compose_markdown(self, title: str, chapters: dict[str, str]) -> str:
        body = [f"# {title} 设计说明书", ""]
        body.extend(chapters[key] for key in sorted(chapters))
        return "\n".join(body)

    def _section_paragraph(self, section: str, analysis: AnalysisResult, previous_summary: str, section_budget: int) -> str:
        modules = "、".join(module.name for module in analysis.core_modules)
        stack = "；".join(f"{key}: {value}" for key, value in analysis.tech_stack.items())
        prior = "前文已经明确了系统边界和核心模块，本节延续这些约束展开设计。" if previous_summary else "本节从项目立项和材料审查角度展开说明。"
        if section_budget < 140:
            return (
                f"{section}说明“{analysis.title}”在{analysis.business_domain}场景下的设计取舍，"
                f"重点保持{analysis.architecture_style}、模块命名和源代码目录一致。"
            )
        return (
            f"{prior}{section}围绕“{analysis.title}”的业务目标展开。系统面向{analysis.business_domain}场景，"
            f"采用{analysis.architecture_style}，核心模块包括{modules}。技术选型为{stack}。"
            "设计时优先保证材料描述、接口命名和源代码结构之间的一致性，使审查人员能够从说明书追溯到对应的代码文件。"
        )

    def _module_function_table(self, analysis: AnalysisResult) -> list[str]:
        lines = ["| 模块 | 主要职责 | 关键接口 |", "|---|---|---|"]
        for module in analysis.core_modules:
            lines.append(f"| {module.name} | {'、'.join(module.responsibilities)} | {'、'.join(module.interfaces[:3])} |")
        lines.append("")
        return lines

    def _database_table(self, analysis: AnalysisResult) -> list[str]:
        lines = ["| 数据表 | 主要字段 | 设计说明 |", "|---|---|---|"]
        for module in analysis.core_modules:
            table_name = module.slug.replace("module_", "biz_")
            fields = "id, name, status, owner_id, created_at, updated_at"
            lines.append(f"| {table_name} | {fields} | 支撑{module.name}的数据记录、状态流转和审计追踪 |")
        lines.append("")
        return lines

    def _interface_table(self, analysis: AnalysisResult) -> list[str]:
        lines = ["| 接口 | 方法 | 输入 | 输出 |", "|---|---|---|---|"]
        for module in analysis.core_modules:
            lines.append(f"| /api/{module.slug}/query | POST | 查询条件、分页参数 | {module.name}分页结果 |")
            lines.append(f"| /api/{module.slug}/save | POST | 表单数据、操作者ID | 保存结果和审计编号 |")
        lines.append("")
        return lines

    def _expansion_paragraph(self, chapter: Chapter, analysis: AnalysisResult, seed: int) -> str:
        module = analysis.core_modules[seed % len(analysis.core_modules)]
        responsibility = module.responsibilities[seed % len(module.responsibilities)]
        return (
            f"在{chapter.title}的实现说明中，{module.name}承担{responsibility}职责。工程实现上，该模块先进行输入校验，"
            "再调用服务层完成业务规则判断，最后将处理结果写入持久化存储并记录审计日志。这样的处理顺序虽然比直接写库多一步，"
            "但可以把权限、数据质量和异常追踪统一收敛，后续扩展缓存、消息队列或模型推理服务时也不需要改变外部接口。"
        )

    def _summarize(self, content: str) -> str:
        compact = " ".join(line.strip() for line in content.splitlines() if line.strip() and not line.startswith("|"))
        return compact[:300]
