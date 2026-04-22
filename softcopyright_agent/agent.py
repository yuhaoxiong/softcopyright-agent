"""Main six-phase orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .aigc_reducer import AIGCReducer
from .analyzer import TitleAnalyzer
from .code_generator import CodeGenerator
from .doc_writer import DocumentWriter
from .llm import LLMClient, LLMError, LLMSettings, create_llm_client
from .models import AnalysisResult, GeneratedFile, Outline, RunConfig, RunResult
from .outline_generator import OutlineGenerator
from .output_formatter import OutputFormatter
from .prompt_engine import PromptEngine
from .review import ReviewManager
from .tools.quality_tool import ChapterQualityChecker


class GenerationCheckpointError(Exception):
    """Exception raised when generation fails midway, carrying the partial state."""
    def __init__(self, message: str, partial_state: dict):
        super().__init__(message)
        self.partial_state = partial_state


class SoftCopyrightAgent:
    """Run the six-phase soft copyright material generation pipeline."""

    def __init__(self) -> None:
        self.analyzer = TitleAnalyzer()
        self.outline_generator = OutlineGenerator()
        self.doc_writer = DocumentWriter()
        self.code_generator = CodeGenerator()
        self.aigc_reducer = AIGCReducer()
        self.output_formatter = OutputFormatter()
        self.prompt_engine = PromptEngine()
        self.quality_checker = ChapterQualityChecker()

    def run(
        self, 
        title: str, 
        config: RunConfig | None = None,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> RunResult:
        config = config or RunConfig()
        output_dir = Path(config.output_dir)
        llm_client = create_llm_client(
            LLMSettings.from_env(
                config.llm_provider,
                api_key=config.llm_api_key,
                model=config.llm_model,
                base_url=config.llm_base_url,
            ),
            required=config.llm_required,
        )
        generation_mode = llm_client.provider_name if llm_client is not None else "fallback"
        review_manager = None
        if config.interactive_review or config.review_dir is not None:
            review_manager = ReviewManager(config.review_dir or output_dir / "review", interactive=config.interactive_review)

        analysis, outline, generation_mode = self.run_analysis_and_outline(
            title, config, llm_client, generation_mode, progress_callback
        )
        
        if config.confirm_outline:
            self._confirm_outline(outline)
        if review_manager is not None:
            outline = review_manager.review_outline(outline)
            
        return self.run_generation(
            title, analysis, outline, config, generation_mode, llm_client, review_manager, progress_callback
        )

    def run_analysis_and_outline(
        self,
        title: str,
        config: RunConfig,
        llm_client: LLMClient | None,
        generation_mode: str,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> tuple[AnalysisResult, Outline, str]:
        """Phase 1 and 2: Generate architecture spec and document outline."""
        self.prompt_engine.theme = config.theme

        # Phase 1: 标题分析（LLM 增强）
        if progress_callback:
            progress_callback("标题分析", 0.0, "正在分析项目标题与推断技术栈...")
        try:
            analysis = self.analyzer.analyze(
                title,
                llm_client=llm_client,
                prompt_engine=self.prompt_engine,
                project_type=config.project_type,
                tech_stack=config.tech_stack,
                database=config.database,
                has_algo="是" if config.has_algo else "否",
                has_mobile="是" if config.has_mobile else "否",
            )
        except (LLMError, ValueError, KeyError) as exc:
            if config.llm_required:
                raise
            generation_mode = f"{generation_mode}+fallback_analysis"
            print(f"标题分析 LLM 失败，已回退到本地分析：{exc}")
            analysis = self.analyzer.analyze(title)

        # Phase 2: 目录生成
        if progress_callback:
            progress_callback("目录生成", 0.2, "正在规划说明书目录结构与源代码组织...")
        try:
            outline = self.outline_generator.generate(
                analysis,
                config.target_doc_words,
                llm_client=llm_client,
                prompt_engine=self.prompt_engine,
            )
        except (LLMError, ValueError, KeyError) as exc:
            if config.llm_required:
                raise
            generation_mode = f"{generation_mode}+fallback_outline"
            print(f"目录 LLM 生成失败，已回退到本地规划：{exc}")
            outline = self.outline_generator.generate(analysis, config.target_doc_words)

        return analysis, outline, generation_mode

    def run_generation(
        self,
        title: str,
        analysis: AnalysisResult,
        outline: Outline,
        config: RunConfig,
        generation_mode: str,
        llm_client: LLMClient | None,
        review_manager: ReviewManager | None,
        progress_callback: Callable[[str, float, str], None] | None = None,
        resume_state: dict | None = None,
    ) -> RunResult:
        """Phase 3-6: Write document, reduce AIGC, generate code, and format output."""
        output_dir = Path(config.output_dir)
        state = resume_state or {}

        # Phase 3: 说明书编写（带质量自检闭环）
        if "document" not in state:
            if progress_callback:
                progress_callback("说明书编写", 0.4, "正在编写各个章节内容...")
            try:
                document = self._write_chapters_with_quality_check(
                    analysis, outline, llm_client, config, progress_callback
                )
            except Exception as exc:
                if not isinstance(exc, LLMError) or config.llm_required:
                    raise GenerationCheckpointError(str(exc), state) from exc
                generation_mode = f"{generation_mode}+fallback_document"
                print(f"说明书 LLM 生成失败，已回退到本地撰写：{exc}")
                document = self.doc_writer.write(analysis, outline, progress_callback=progress_callback)
            state["document"] = document

        document = state["document"]

        # Phase 5: AIGC 降重（LLM 增强 + 多轮）
        if "reduced_document" not in state:
            if progress_callback:
                progress_callback("说明书降重", 0.6, "正在改写说明书以降低 AI 生成感...")
            try:
                reduced_document = self.aigc_reducer.reduce_document(
                    document,
                    llm_client=llm_client,
                    prompt_engine=self.prompt_engine,
                    rounds=config.aigc_rounds,
                    progress_callback=progress_callback,
                )
            except Exception as exc:
                if not isinstance(exc, LLMError) or config.llm_required:
                    raise GenerationCheckpointError(str(exc), state) from exc
                generation_mode = f"{generation_mode}+fallback_aigc"
                print(f"AIGC 降重 LLM 失败，已回退到确定性替换：{exc}")
                reduced_document = self.aigc_reducer.reduce_document(document, progress_callback=progress_callback)
            
            if review_manager is not None:
                reduced_document = review_manager.review_document(reduced_document)
            state["reduced_document"] = reduced_document

        reduced_document = state["reduced_document"]

        # Phase 4: 代码生成
        if "code_files" not in state:
            if progress_callback:
                progress_callback("源代码生成", 0.8, "正在生成业务模块的示例代码...")
            try:
                code_files = self.code_generator.generate(
                    analysis,
                    outline,
                    config.target_code_lines,
                    document_chapters=reduced_document,
                    llm_client=llm_client,
                    prompt_engine=self.prompt_engine,
                    progress_callback=progress_callback,
                )
            except Exception as exc:
                if not isinstance(exc, (LLMError, ValueError, KeyError)) or config.llm_required:
                    raise GenerationCheckpointError(str(exc), state) from exc
                generation_mode = f"{generation_mode}+fallback_code"
                print(f"源代码 LLM 生成失败，已回退到本地生成：{exc}")
                code_files = self.code_generator.generate(
                    analysis,
                    outline,
                    config.target_code_lines,
                    document_chapters=reduced_document,
                    progress_callback=progress_callback,
                )
            if review_manager is not None:
                code_files = review_manager.review_code(code_files)
            state["code_files"] = code_files

        code_files = state["code_files"]

        # Phase 6: 整理输出
        if progress_callback:
            progress_callback("整理输出", 0.95, "正在计算质量得分并打包输出文件...")
        formatted = self.output_formatter.format(
            title=analysis.title,
            output_dir=output_dir,
            analysis=analysis,
            outline=outline,
            document_chapters=reduced_document,
            code_files=code_files,
            target_doc_words=config.target_doc_words,
            target_code_lines=config.target_code_lines,
            create_docx=config.create_docx,
            enable_remote_diagrams=config.enable_remote_diagrams,
            generation_mode=generation_mode,
            review_dir=(review_manager.review_dir if review_manager is not None else None),
        )
        files = {key: value for key, value in formatted.items() if isinstance(value, Path)}
        return RunResult(
            title=analysis.title,
            output_dir=Path(config.output_dir),
            analysis=analysis,
            outline=outline,
            document_words=int(formatted["document_words"]),
            source_lines=int(formatted["source_lines"]),
            files=files,
            document_chapters=reduced_document,
            generation_mode=generation_mode,
            quality_metrics=formatted["quality_metrics"],
        )

    def regenerate_chapter(
        self,
        chapter_id: str,
        outline: Outline,
        analysis: AnalysisResult,
        document_chapters: dict[str, str],
        llm_client: LLMClient | None,
    ) -> str:
        """Regenerate a single chapter's content and return it directly."""
        chapter = next((c for c in outline.chapters if c.id == chapter_id), None)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found in outline.")
        
        # We need a context of what's generated so far.
        # But we only pass prior chapters.
        previous_summary = ""
        for c in outline.chapters:
            if c.id == chapter_id:
                break
            if c.id in document_chapters:
                previous_summary = (previous_summary + "\n" + self.doc_writer._summarize(document_chapters[c.id]))[-1200:]
        
        return self.doc_writer.write_chapter(
            chapter=chapter,
            analysis=analysis,
            previous_summary=previous_summary,
            outline=outline,
            llm_client=llm_client,
            prompt_engine=self.prompt_engine,
        )

    def format_document(
        self,
        title: str,
        analysis: AnalysisResult,
        outline: Outline,
        document_chapters: dict[str, str],
        code_files: list[GeneratedFile],
        config: RunConfig,
        generation_mode: str,
    ) -> RunResult:
        """Repackage document after manual chapters modification."""
        formatted = self.output_formatter.format(
            title=title,
            output_dir=Path(config.output_dir),
            analysis=analysis,
            outline=outline,
            document_chapters=document_chapters,
            code_files=code_files,
            target_doc_words=config.target_doc_words,
            target_code_lines=config.target_code_lines,
            create_docx=config.create_docx,
            enable_remote_diagrams=config.enable_remote_diagrams,
            generation_mode=generation_mode,
            review_dir=None,  # skip drafting on manual reformat
        )
        files = {key: value for key, value in formatted.items() if isinstance(value, Path)}
        return RunResult(
            title=title,
            output_dir=Path(config.output_dir),
            analysis=analysis,
            outline=outline,
            document_words=int(formatted["document_words"]),
            source_lines=int(formatted["source_lines"]),
            files=files,
            document_chapters=document_chapters,
            generation_mode=generation_mode,
            quality_metrics=formatted["quality_metrics"],
        )

    def _write_chapters_with_quality_check(
        self,
        analysis: AnalysisResult,
        outline: Outline,
        llm_client: LLMClient | None,
        config: RunConfig,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> dict[str, str]:
        """Write chapters with quality self-check and retry loop.

        After each chapter is generated, the quality checker evaluates it.
        If the score falls below ``config.chapter_quality_threshold`` and
        retries remain, the checker's observation is injected as feedback
        into the next attempt, giving the LLM specific instructions on
        what to fix.
        """
        chapters: dict[str, str] = {}
        previous_summary = ""
        total = len(outline.chapters)

        for i, chapter in enumerate(outline.chapters):
            quality_feedback: str | None = None

            for attempt in range(config.max_chapter_retries + 1):
                if progress_callback:
                    retry_hint = f" (重试 {attempt}/{config.max_chapter_retries})" if attempt > 0 else ""
                    progress_callback(
                        "说明书编写",
                        0.4 + 0.2 * (i / max(total, 1)),
                        f"正在编写：{chapter.title} ({i + 1}/{total}){retry_hint}",
                    )

                content = self.doc_writer.write_chapter(
                    chapter,
                    analysis,
                    previous_summary,
                    outline=outline,
                    llm_client=llm_client,
                    prompt_engine=self.prompt_engine,
                    quality_feedback=quality_feedback,
                )

                # Self-check: only when LLM is active and retries remain
                if llm_client is not None and attempt < config.max_chapter_retries:
                    check = self.quality_checker.check(chapter.id, content, chapter)
                    if check.data["score"] >= config.chapter_quality_threshold:
                        if attempt > 0 and progress_callback:
                            progress_callback(
                                "说明书编写",
                                0.4 + 0.2 * (i / max(total, 1)),
                                f"{chapter.title} 质量自检通过 ({check.data['score']}分)",
                            )
                        break
                    # Below threshold: inject feedback for next attempt
                    quality_feedback = check.observation
                    if progress_callback:
                        progress_callback(
                            "说明书编写",
                            0.4 + 0.2 * (i / max(total, 1)),
                            f"{chapter.title} 质量不达标({check.data['score']}分)，准备重写...",
                        )
                else:
                    break

            chapters[chapter.id] = content
            previous_summary = (previous_summary + "\n" + self.doc_writer._summarize(content))[-1200:]

        return chapters

    def _confirm_outline(self, outline) -> None:
        print("即将生成以下目录：")
        for chapter in outline.chapters:
            print(f"- {chapter.title}")
            for section in chapter.sections[:8]:
                print(f"  - {section}")
        answer = input("继续生成？[y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            raise RuntimeError("用户取消生成")
