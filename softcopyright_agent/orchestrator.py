"""ReAct orchestrator — LLM-driven pipeline execution.

Replaces the hardcoded six-phase pipeline with a Think→Act→Observe loop
where the LLM autonomously plans and executes tool calls.

Usage:
    orchestrator = ReActOrchestrator(llm_client, components, config)
    result = orchestrator.run("智能分拣系统V1.0")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .aigc_reducer import AIGCReducer
from .analyzer import TitleAnalyzer
from .code_generator import CodeGenerator
from .doc_writer import DocumentWriter
from .llm import LLMClient
from .memory import AgentMemory
from .models import (
    AnalysisResult,
    GeneratedFile,
    Outline,
    RunConfig,
    RunResult,
)
from .output_formatter import OutputFormatter
from .prompt_engine import PromptEngine
from .tools.base import ToolResult
from .tools.quality_tool import ChapterQualityChecker
from .tools.registry import ToolRegistry, ToolSpec

# ── AgentState ───────────────────────────────────────────────────


@dataclass
class AgentState:
    """Shared mutable state that all tools read from and write to."""

    title: str = ""
    analysis: AnalysisResult | None = None
    outline: Outline | None = None
    chapters: dict[str, str] = field(default_factory=dict)
    reduced_chapters: dict[str, str] = field(default_factory=dict)
    code_files: list[GeneratedFile] = field(default_factory=list)
    quality_scores: dict[str, int] = field(default_factory=dict)
    generation_mode: str = "react"
    _previous_summary: str = ""


# ── Action Parsing ───────────────────────────────────────────────

_THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\nAction:)", re.DOTALL)
_ACTION_RE = re.compile(r"Action:\s*(\w+)")
_INPUT_RE = re.compile(r"Action Input:\s*(\{.*?\})", re.DOTALL)


@dataclass(slots=True)
class ParsedAction:
    """Result of parsing the LLM's ReAct response."""

    thought: str
    tool_name: str
    tool_input: dict[str, Any]


def parse_action(response: str) -> ParsedAction:
    """Extract Thought, Action, and Action Input from an LLM response."""
    thought_m = _THOUGHT_RE.search(response)
    action_m = _ACTION_RE.search(response)
    input_m = _INPUT_RE.search(response)

    thought = thought_m.group(1).strip() if thought_m else ""
    tool_name = action_m.group(1).strip() if action_m else ""
    try:
        tool_input = json.loads(input_m.group(1)) if input_m else {}
    except json.JSONDecodeError:
        tool_input = {}

    return ParsedAction(thought=thought, tool_name=tool_name, tool_input=tool_input)


# ── System Prompt ────────────────────────────────────────────────

_SYSTEM_PROMPT = """你是「软著材料生成 Agent」。你的任务是根据用户提供的软件标题，通过调用工具逐步生成完整的软著申请材料。

## 可用工具

{tool_list}

## 工作规则

1. **必须先** `analyze_title`，**再** `generate_outline`
2. 按章节顺序依次调用 `write_chapter`（chapter_1 → chapter_7 → appendix，如有）
3. **每写完一章必须** `check_quality`，质量分 < 70 时**必须重写该章**（最多重试 2 次）
4. 所有章节写完后，依次 `reduce_chapter` 降重
5. 降重完成后，调用 `generate_all_code` 生成全部源代码
6. 最后调用 `finish` 完成打包

## 输出格式

每一步严格按以下格式输出，**不要输出其他任何内容**：

Thought: <你的判断和推理>
Action: <工具名称>
Action Input: <JSON 参数对象>

当所有任务完成时：
Thought: 所有材料已生成完毕
Action: finish
Action Input: {{}}"""


# ── Orchestrator ─────────────────────────────────────────────────


class ReActOrchestrator:
    """LLM-driven ReAct loop that replaces the fixed pipeline.

    The orchestrator:
    1. Registers all pipeline components as named tools
    2. Builds a system prompt with tool descriptions
    3. Runs a Think→Act→Observe loop until the LLM calls `finish`
    """

    def __init__(
        self,
        llm_client: LLMClient,
        *,
        analyzer: TitleAnalyzer,
        outline_generator: "OutlineGenerator",
        doc_writer: DocumentWriter,
        quality_checker: ChapterQualityChecker,
        aigc_reducer: AIGCReducer,
        code_generator: CodeGenerator,
        output_formatter: OutputFormatter,
        prompt_engine: PromptEngine,
        config: RunConfig,
        progress_callback: Callable[[str, float, str], None] | None = None,
        max_steps: int = 50,
    ) -> None:
        from .outline_generator import OutlineGenerator

        self.llm = llm_client
        self.config = config
        self.prompt_engine = prompt_engine
        self.progress_callback = progress_callback
        self.max_steps = max_steps

        # Components (kept as instance vars for tool closures)
        self._analyzer = analyzer
        self._outline_gen = outline_generator
        self._doc_writer = doc_writer
        self._quality_checker = quality_checker
        self._aigc_reducer = aigc_reducer
        self._code_gen = code_generator
        self._output_formatter = output_formatter

        # Shared state + memory
        self.state = AgentState()
        self.memory = AgentMemory()
        self.registry = ToolRegistry()
        self._register_tools()

    # ── Tool Registration ────────────────────────────────────────

    def _register_tools(self) -> None:
        """Create closures over self.state and register all tools."""
        R = self.registry.register

        R(ToolSpec(
            name="analyze_title",
            description="分析软著标题，推断技术栈、业务领域和核心模块规划",
            parameters={"title": "软著标题字符串"},
            handler=self._tool_analyze,
        ))
        R(ToolSpec(
            name="generate_outline",
            description="基于分析结果生成符合 CPCC 规范的七章目录结构",
            parameters={"target_words": "目标总字数(int)"},
            handler=self._tool_outline,
        ))
        R(ToolSpec(
            name="write_chapter",
            description="编写指定章节的设计说明书内容",
            parameters={"chapter_id": "章节ID(如 chapter_1)", "feedback": "质量反馈(可选)"},
            handler=self._tool_write_chapter,
        ))
        R(ToolSpec(
            name="check_quality",
            description="检查指定章节的质量评分(字数/图表/编号/表格/子节/纯净度)",
            parameters={"chapter_id": "章节ID"},
            handler=self._tool_check_quality,
        ))
        R(ToolSpec(
            name="reduce_chapter",
            description="对指定章节执行 AIGC 降重改写",
            parameters={"chapter_id": "章节ID"},
            handler=self._tool_reduce_chapter,
        ))
        R(ToolSpec(
            name="generate_all_code",
            description="根据分析和大纲生成全部模块的源代码",
            parameters={},
            handler=self._tool_generate_code,
        ))
        R(ToolSpec(
            name="finish",
            description="所有材料已完成，执行打包输出",
            parameters={},
            handler=self._tool_finish,
        ))

    # ── Tool Implementations ─────────────────────────────────────

    def _tool_analyze(self, title: str = "", **_: Any) -> ToolResult:
        title = title or self.state.title
        self.state.title = title
        self.prompt_engine.theme = self.config.theme
        try:
            analysis = self._analyzer.analyze(
                title,
                llm_client=self.llm,
                prompt_engine=self.prompt_engine,
                project_type=self.config.project_type,
                tech_stack=self.config.tech_stack,
                database=self.config.database,
                has_algo="是" if self.config.has_algo else "否",
                has_mobile="是" if self.config.has_mobile else "否",
            )
        except Exception:
            analysis = self._analyzer.analyze(title)

        self.state.analysis = analysis
        modules = ", ".join(m.name for m in analysis.core_modules)
        return ToolResult(
            success=True,
            data={"modules_count": len(analysis.core_modules)},
            observation=f"标题分析完成。业务领域: {analysis.business_domain}。"
            f"核心模块({len(analysis.core_modules)}个): {modules}",
        )

    def _tool_outline(self, target_words: int = 0, **_: Any) -> ToolResult:
        if self.state.analysis is None:
            return ToolResult(success=False, data={}, observation="请先调用 analyze_title")
        target = int(target_words) if target_words else self.config.target_doc_words
        try:
            outline = self._outline_gen.generate(
                self.state.analysis, target,
                llm_client=self.llm, prompt_engine=self.prompt_engine,
            )
        except Exception:
            outline = self._outline_gen.generate(self.state.analysis, target)

        self.state.outline = outline
        ch_list = ", ".join(c.title for c in outline.chapters)
        return ToolResult(
            success=True,
            data={"chapters_count": len(outline.chapters)},
            observation=f"大纲生成完成。包含 {len(outline.chapters)} 章: {ch_list}",
        )

    def _tool_write_chapter(self, chapter_id: str = "", feedback: str = "", **_: Any) -> ToolResult:
        if not self.state.outline or not self.state.analysis:
            return ToolResult(success=False, data={}, observation="请先完成 analyze_title 和 generate_outline")
        chapter = next((c for c in self.state.outline.chapters if c.id == chapter_id), None)
        if chapter is None:
            ids = [c.id for c in self.state.outline.chapters]
            return ToolResult(success=False, data={}, observation=f"章节 {chapter_id} 不存在。可用: {ids}")

        content = self._doc_writer.write_chapter(
            chapter,
            self.state.analysis,
            self.state._previous_summary,
            outline=self.state.outline,
            llm_client=self.llm,
            prompt_engine=self.prompt_engine,
            quality_feedback=feedback or None,
        )
        self.state.chapters[chapter_id] = content
        self.state._previous_summary = (
            self.state._previous_summary + "\n" + self._doc_writer._summarize(content)
        )[-1200:]

        from .utils.word_counter import count_words
        wc = count_words(content)
        return ToolResult(
            success=True,
            data={"chapter_id": chapter_id, "word_count": wc},
            observation=f"章节 {chapter_id}({chapter.title}) 编写完成，字数: {wc}",
        )

    def _tool_check_quality(self, chapter_id: str = "", **_: Any) -> ToolResult:
        content = self.state.chapters.get(chapter_id, "")
        if not content:
            return ToolResult(success=False, data={}, observation=f"章节 {chapter_id} 尚未编写")
        chapter = next((c for c in (self.state.outline or Outline([], {})).chapters if c.id == chapter_id), None)
        if chapter is None:
            return ToolResult(success=False, data={}, observation=f"章节 {chapter_id} 不在大纲中")

        result = self._quality_checker.check(chapter_id, content, chapter)
        self.state.quality_scores[chapter_id] = result.data["score"]
        return result

    def _tool_reduce_chapter(self, chapter_id: str = "", **_: Any) -> ToolResult:
        content = self.state.chapters.get(chapter_id, "")
        if not content:
            return ToolResult(success=False, data={}, observation=f"章节 {chapter_id} 尚未编写")
        try:
            reduced = self._aigc_reducer.reduce_document(
                {chapter_id: content},
                llm_client=self.llm,
                prompt_engine=self.prompt_engine,
                rounds=self.config.aigc_rounds,
            )
        except Exception:
            reduced = self._aigc_reducer.reduce_document({chapter_id: content})

        self.state.reduced_chapters[chapter_id] = reduced[chapter_id]
        return ToolResult(
            success=True,
            data={"chapter_id": chapter_id},
            observation=f"章节 {chapter_id} AIGC 降重完成",
        )

    def _tool_generate_code(self, **_: Any) -> ToolResult:
        if not self.state.analysis or not self.state.outline:
            return ToolResult(success=False, data={}, observation="请先完成分析和大纲")
        doc_chapters = self.state.reduced_chapters or self.state.chapters
        try:
            files = self._code_gen.generate(
                self.state.analysis,
                self.state.outline,
                self.config.target_code_lines,
                document_chapters=doc_chapters,
                llm_client=self.llm,
                prompt_engine=self.prompt_engine,
            )
        except Exception:
            files = self._code_gen.generate(
                self.state.analysis, self.state.outline, self.config.target_code_lines,
            )
        self.state.code_files = files
        total_lines = sum(f.line_count for f in files)
        return ToolResult(
            success=True,
            data={"file_count": len(files), "total_lines": total_lines},
            observation=f"源代码生成完成: {len(files)} 个文件, 共 {total_lines} 行",
        )

    def _tool_finish(self, **_: Any) -> ToolResult:
        return ToolResult(
            success=True,
            data={"finished": True},
            observation="任务标记完成。正在打包输出...",
        )

    # ── ReAct Loop ───────────────────────────────────────────────

    def run(self, title: str) -> RunResult:
        """Execute the full ReAct loop and return a RunResult."""
        self.state.title = title
        self.memory.add("user", f"请为「{title}」生成完整的软著申请材料（说明书+源代码）。"
                         f"目标字数: {self.config.target_doc_words}，目标代码行数: {self.config.target_code_lines}。")

        system_prompt = _SYSTEM_PROMPT.format(
            tool_list=self.registry.format_for_prompt()
        )

        for step in range(self.max_steps):
            # Report progress
            progress = min(0.95, step / max(self.max_steps, 1))
            if self.progress_callback:
                tools_done = self.memory.get_tools_called()
                self.progress_callback(
                    "Agent 执行",
                    progress,
                    f"步骤 {step + 1}: 已完成 {len(tools_done)} 个工具调用",
                )

            # Think: ask LLM what to do next
            context = self.memory.get_context()
            response = self.llm.generate(
                system=system_prompt,
                user=context + "\n\n请决定下一步操作：",
                temperature=0.2,
            )

            # Parse the action
            action = parse_action(response)
            if not action.tool_name:
                # LLM didn't produce a valid action; nudge it
                self.memory.add("observation", "无法解析你的输出。请严格按 Thought/Action/Action Input 格式回答。")
                continue

            # Record thought
            if action.thought:
                self.memory.add("thought", action.thought)

            # Check for finish
            if action.tool_name == "finish":
                self.memory.add("action", "任务完成", tool_name="finish")
                break

            # Act: execute the tool
            self.memory.add("action", json.dumps(action.tool_input, ensure_ascii=False), tool_name=action.tool_name)
            result = self.registry.execute(action.tool_name, **action.tool_input)

            # Observe: record the result
            self.memory.add("observation", result.observation)

        # Package the final result
        return self._build_result()

    def _build_result(self) -> RunResult:
        """Package AgentState into a RunResult."""
        output_dir = Path(self.config.output_dir)
        doc_chapters = self.state.reduced_chapters or self.state.chapters
        code_files = self.state.code_files

        if not self.state.analysis or not self.state.outline:
            raise RuntimeError("Agent 未完成标题分析或大纲生成")

        formatted = self._output_formatter.format(
            title=self.state.analysis.title,
            output_dir=output_dir,
            analysis=self.state.analysis,
            outline=self.state.outline,
            document_chapters=doc_chapters,
            code_files=code_files,
            target_doc_words=self.config.target_doc_words,
            target_code_lines=self.config.target_code_lines,
            create_docx=self.config.create_docx,
            enable_remote_diagrams=self.config.enable_remote_diagrams,
            generation_mode=self.state.generation_mode,
        )
        files = {k: v for k, v in formatted.items() if isinstance(v, Path)}
        return RunResult(
            title=self.state.analysis.title,
            output_dir=output_dir,
            analysis=self.state.analysis,
            outline=self.state.outline,
            document_words=int(formatted["document_words"]),
            source_lines=int(formatted["source_lines"]),
            files=files,
            document_chapters=doc_chapters,
            generation_mode="react",
            quality_metrics=formatted["quality_metrics"],
        )
