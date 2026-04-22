"""Streamlit UI for the soft copyright agent.

Run with:
    python -m streamlit run softcopyright_agent/ui.py
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import io
import json
import time

from softcopyright_agent.agent import SoftCopyrightAgent, GenerationCheckpointError
from softcopyright_agent.llm import LLMSettings, create_llm_client
from softcopyright_agent.models import RunConfig, AnalysisResult, Outline


TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def iter_display_files(root: Path) -> list[Path]:
    """Return displayable files below a root, with text files first."""

    if not root.exists():
        return []
    files = [path for path in root.rglob("*") if path.is_file()]
    return sorted(files, key=lambda path: (path.suffix.lower() not in TEXT_SUFFIXES, str(path).lower()))


def relative_label(path: Path, root: Path) -> str:
    """Return a stable UI label for a file."""

    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def language_for(path: Path) -> str:
    mapping = {
        ".css": "css",
        ".html": "html",
        ".js": "javascript",
        ".json": "json",
        ".md": "markdown",
        ".py": "python",
        ".sql": "sql",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    return mapping.get(path.suffix.lower(), "text")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def zip_directory(root: Path) -> bytes:
    """Create an in-memory zip archive for download."""

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for path in sorted(file for file in root.rglob("*") if file.is_file()):
            archive.write(path, path.relative_to(root).as_posix())
    return buffer.getvalue()


def _get_llm_client(config: RunConfig):
    """Build an LLM client from RunConfig (unified factory)."""
    return create_llm_client(
        LLMSettings.from_env(
            config.llm_provider,
            api_key=config.llm_api_key,
            model=config.llm_model,
            base_url=config.llm_base_url,
        ),
        required=config.llm_required,
    )


def _render_summary(result_data: dict) -> None:
    """Render quality metrics and metadata summary."""
    import streamlit as st

    st.subheader("生成摘要")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("说明书字数", result_data.get("document_words", 0))
    col2.metric("源代码行数", result_data.get("source_lines", 0))
    col3.metric("生成模式", result_data.get("generation_mode", "unknown"))

    qm = result_data.get("quality_metrics")
    if qm:
        col4.metric("质量评估得分", f"{qm.get('total_score', 0)} / 100")
        st.caption(f"评估详情：{qm.get('assessment_detail', '无')}")
    else:
        col4.metric("质量评估得分", "未评估")

    with st.expander("运行元数据"):
        st.json(result_data)


def run_app() -> None:
    import streamlit as st

    st.set_page_config(page_title="软著编写 Agent", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
    
    from softcopyright_agent.ui_styler import apply_premium_styling
    apply_premium_styling()

    st.title("⚡ 软著编写智能体 工厂")
    st.caption("大模型驱动的软著说明书与源代码素材生成，支持人工审查和在线修改。")

    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_output_dir" not in st.session_state:
        st.session_state.last_output_dir = Path("outputs/ui-run")
    if "last_review_dir" not in st.session_state:
        st.session_state.last_review_dir = Path("outputs/ui-review")
    if "tmp_resume_state" not in st.session_state:
        st.session_state.tmp_resume_state = None
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = "IDLE"  # IDLE, OUTLINE_REVIEW, DONE
    if "tmp_analysis" not in st.session_state:
        st.session_state.tmp_analysis = None
    if "tmp_outline" not in st.session_state:
        st.session_state.tmp_outline = None
    if "tmp_config" not in st.session_state:
        st.session_state.tmp_config = None
    if "tmp_mode" not in st.session_state:
        st.session_state.tmp_mode = None

    tab_setup, tab_plan, tab_gen, tab_out = st.tabs([
        "1. 配置与标题 ⚙️", 
        "2. 规划审查 🧠", 
        "3. 内容生成 🏭", 
        "4. 输出与库房 📦"
    ])

    with tab_setup:
        st.header("项目环境构建中心")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("基本信息")
            title = st.text_input("软著标题", value="基于深度学习的智能问答系统 V1.0")
            output_dir = Path(st.text_input("输出目录", value=str(st.session_state.last_output_dir)))
            review_dir = Path(st.text_input("审查草稿目录", value=str(st.session_state.last_review_dir)))
            doc_words = st.number_input("说明书目标字数", min_value=800, max_value=20000, value=9000, step=500)
            code_lines = st.number_input("源代码目标行数", min_value=200, max_value=20000, value=3000, step=200)
            
            project_type = st.selectbox("业务类型向导", ["管理系统", "平台框架", "数据分析", "AI 问答/算法", "移动/小程序", "物联网监控", "默认模式"], index=6)
            tech_stack = st.text_input("架构栈", value="默认")
            database = st.text_input("数据库引擎", value="默认")
            
        with col_c2:
            st.subheader("平台偏好")
            has_algo = st.checkbox("强制规划 AI / 算法硬核模块")
            has_mobile = st.checkbox("强制规划移动端/小程序入口")
            create_docx = st.checkbox("导出 DOCX", value=True)
            enable_remote_diagrams = st.checkbox("启用 Kroki 渲染图表", value=True)
            
            st.divider()
            st.subheader("模型配置")
            llm_provider = st.selectbox("LLM Provider", ["auto", "openai-compatible", "grok", "fallback"], index=0)
            llm_api_key = st.text_input("API Key", type="password", placeholder="不填写则读取环境变量")
            llm_model = st.text_input("模型名", value="", placeholder="例如 gpt-4o-mini 或 grok-4")
            llm_base_url = st.text_input("Base URL", value="", placeholder="例如 https://api.openai.com/v1")
            llm_required = st.checkbox("必须使用大模型，失败不回退", value=False)
            aigc_rounds = st.number_input("AIGC 降重轮次", min_value=1, max_value=5, value=1, step=1)
            write_review = st.checkbox("生成审查草稿", value=True)
            theme = st.selectbox("输出主题模板", ["standard", "game", "algorithm", "frontend_only", "iot"], index=0)

        # Build config
        from softcopyright_agent.models import RunConfig
        config = RunConfig(
            output_dir=output_dir,
            target_doc_words=int(doc_words),
            target_code_lines=int(code_lines),
            create_docx=create_docx,
            enable_remote_diagrams=enable_remote_diagrams,
            llm_provider=llm_provider,
            llm_api_key=llm_api_key or None,
            llm_model=llm_model or None,
            llm_base_url=llm_base_url or None,
            llm_required=llm_required,
            aigc_rounds=int(aigc_rounds),
            review_dir=review_dir if write_review else None,
            theme=theme,
            project_type=project_type,
            tech_stack=tech_stack,
            database=database,
            has_algo=has_algo,
            has_mobile=has_mobile
        )

        st.divider()
        if st.session_state.agent_state == "IDLE" or st.session_state.agent_state == "DONE":
            start_phase1_btn = st.button("🚀 启动第一阶段：规划与立项分析", type="primary", use_container_width=True)
        else:
            start_phase1_btn = False
            if st.session_state.agent_state == "OUTLINE_REVIEW":
                st.info("架构已产出：请前往【2. 规划审查】标签卡检查。")
            if st.button("取消会话并复位系统", key="reset_bt1"):
                st.session_state.agent_state = "IDLE"
                st.rerun()

    if start_phase1_btn:
        if not title.strip():
            st.error("请输入软著标题。")
            return
        
        st.session_state.tmp_config = config
        with st.status("正在进行需求分析与架构规划...", expanded=True) as status:
            progress_bar = st.progress(0.0)
            progress_text = st.empty()

            def _on_progress(phase: str, pct: float, detail: str) -> None:
                progress_bar.progress(min(1.0, max(0.0, pct)))
                progress_text.text(f"【{phase}】 {detail}")

            llm_client = _get_llm_client(config)
            mode = llm_client.provider_name if llm_client else "fallback"

            try:
                import time
                started = time.time()
                analysis, outline, mode = SoftCopyrightAgent().run_analysis_and_outline(
                    title, config, llm_client, mode, progress_callback=_on_progress
                )
            except Exception as exc:
                status.update(label="分析失败", state="error")
                st.exception(exc)
                return
            progress_bar.progress(1.0)
            progress_text.text("大纲规划成功！请进行人工审校。")
            status.update(label=f"规划完成，用时 {time.time() - started:.1f}s", state="complete")
        
        st.session_state.tmp_analysis = analysis
        st.session_state.tmp_outline = outline
        st.session_state.tmp_mode = mode
        st.session_state.agent_state = "OUTLINE_REVIEW"
        st.rerun()

    with tab_plan:
        if st.session_state.agent_state == "OUTLINE_REVIEW":
            st.header("👀 阶段一完成：修改并确认架构规划")
            st.info("系统会自动停在这里。你可以直接在下面的 JSON 编辑框里插入自己想要的图表章节或模块，然后提交到第三步", icon="ℹ️")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("核心模块分析 (Analysis)")
                import json
                analysis_json = json.dumps(st.session_state.tmp_analysis.to_dict(), ensure_ascii=False, indent=2)
                edited_analysis_str = st.text_area("编辑模块定义 JSON", value=analysis_json, height=500)
            with col2:
                st.subheader("生成大纲与结构 (Outline)")
                outline_json = json.dumps(st.session_state.tmp_outline.to_dict(), ensure_ascii=False, indent=2)
                edited_outline_str = st.text_area("编辑目录结构 JSON", value=outline_json, height=500)
                
            if st.button("✅ 阶段二审查通过，放行全卷打字机", type="primary", use_container_width=True):
                try:
                    new_analysis = AnalysisResult.from_dict(json.loads(edited_analysis_str))
                    new_outline = Outline.from_dict(json.loads(edited_outline_str))
                    
                    st.session_state.tmp_analysis = new_analysis
                    st.session_state.tmp_outline = new_outline
                    st.session_state.agent_state = "GENERATING"
                    st.rerun()
                except Exception as e:
                    st.error(f"JSON 格式错误: {e}")
        elif st.session_state.agent_state == "IDLE":
            st.info("暂无待审查大纲，请在【配置与标题】启动分析")

    with tab_gen:
        if st.session_state.agent_state == "GENERATING":
            config = st.session_state.tmp_config
            import time
            started = time.time()
            with st.status("正在基于大纲执行最终材料合成...", expanded=True) as status:
                progress_bar = st.progress(0.0)
                progress_text = st.empty()

                def _on_progress(phase: str, pct: float, detail: str) -> None:
                    progress_bar.progress(min(1.0, max(0.0, pct)))
                    progress_text.text(f"【{phase}】 {detail}")

                llm_client = _get_llm_client(config)

                try:
                    agent = SoftCopyrightAgent()
                    result = agent.run_generation(
                        title, 
                        st.session_state.tmp_analysis, 
                        st.session_state.tmp_outline, 
                        config, 
                        st.session_state.tmp_mode,
                        llm_client, 
                        None,
                        progress_callback=_on_progress,
                        resume_state=st.session_state.tmp_resume_state
                    )
                except Exception as exc:  
                    if type(exc).__name__ == "GenerationCheckpointError":
                        st.session_state.tmp_resume_state = getattr(exc, "partial_state", None)
                        status.update(label="生成已被中断保存", state="error")
                        st.error(f"报错退出，但我们已截获断点: {exc}")
                        st.session_state.agent_state = "GENERATING_ERROR"
                    else:
                        status.update(label="生成失败", state="error")
                        st.exception(exc)
                        st.session_state.agent_state = "IDLE"
                    st.stop()
                    
                st.session_state.tmp_resume_state = None
                progress_bar.progress(1.0)
                progress_text.text("全卷生成成功！")
                status.update(label=f"整个生成流程已完成，用时 {time.time() - started:.1f}s", state="complete")
            
            st.session_state.last_result = result.to_dict()
            st.session_state.last_output_dir = config.output_dir
            st.session_state.last_review_dir = config.review_dir
            st.session_state.agent_state = "DONE"
            st.rerun()
        elif st.session_state.agent_state == "GENERATING_ERROR":
            st.error("执行在生成阶段中途失败，我们已为您保存了所有尚未销毁的文本和代码断点。")
            col_resume, col_restart = st.columns(2)
            if col_resume.button("🔧 继续执行 (利用最后断点恢复)", type="primary", use_container_width=True):
                 st.session_state.agent_state = "GENERATING"
                 st.rerun()
            if col_restart.button("清空断点，重新生成整卷", type="secondary", use_container_width=True):
                 st.session_state.tmp_resume_state = None
                 st.session_state.agent_state = "GENERATING"
                 st.rerun()
        elif st.session_state.agent_state == "DONE":
            st.success("材料已生成，请前往【输出与修改】标签验证成果。")
            if st.button("强行覆盖重生成整卷材料 (Skip Phase 1)", type="secondary"):
                 st.session_state.agent_state = "GENERATING"
                 st.rerun()

    with tab_out:
        if st.session_state.agent_state == "DONE" and st.session_state.last_result:
            _render_summary(st.session_state.last_result)
            output_root = Path(st.session_state.last_output_dir)
            review_root = Path(str(st.session_state.last_review_dir)) if st.session_state.last_review_dir else None
            
            t1, t2, t3, t4 = st.tabs(["生成结果", "纯源文件浏览器", "审查草稿", "历史回放厅"])
            with t1:
                _render_file_browser(output_root, title="最终输出件库", editable=False)
            with t2:
                _render_file_editor(output_root)
            with t3:
                _render_visual_review(st.session_state.last_result, config)
            with t4:
                _render_history_preview()
        else:
            st.info("等待生成完毕以显示输出件，或者可以直接前往历史厅回载：")
            _render_history_preview()

def _render_visual_review(result_data: dict, config: RunConfig) -> None:
    import streamlit as st
    import difflib
    import os
    from pathlib import Path
    from softcopyright_agent.agent import SoftCopyrightAgent
    from softcopyright_agent.models import AnalysisResult, Outline, GeneratedFile
    from softcopyright_agent.llm import LLMSettings, create_llm_client

    st.subheader("高阶审查与修正台")
    chapters = result_data.get("document_chapters", {})
    if not chapters:
        st.info("该运行结果未包含章节级别的数据，无法启动分段审查。请使用新版 Agent 重新运行。")
        return

    # In session_state, we hold our draft and original versions
    if "review_chapters" not in st.session_state:
        st.session_state.review_chapters = dict(chapters)
    
    # We allow the user to modify text
    for ch_id, original_text in chapters.items():
        with st.expander(f"📖 章节审查与 Diff: {ch_id}"):
            current_draft = st.session_state.review_chapters.get(ch_id, original_text)
            
            # Show DIFF if changed
            if current_draft != original_text:
                st.caption("检测到变更 (Diff)：")
                diff = difflib.unified_diff(original_text.splitlines(), current_draft.splitlines(), lineterm="")
                st.code("\n".join(diff), language="diff")

            # 文本修改
            edited_text = st.text_area(
                "请在此处修改", 
                value=current_draft, 
                height=300, 
                key=f"review_text_{ch_id}"
            )
            
            # 操作栏
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💾 保存当前章修改", key=f"review_save_{ch_id}"):
                    st.session_state.review_chapters[ch_id] = edited_text
                    st.success("已暂存该章节。如需生效请点击下方重新打包。")
                    st.rerun()
            with col2:
                if st.button("🔄 使用 AI 重写此章节", key=f"review_regen_{ch_id}", type="secondary"):
                    with st.spinner("AI 正在重写该章节全文..."):
                        llm_client = _get_llm_client(config)
                        agent = SoftCopyrightAgent()
                        try:
                            analysis = AnalysisResult.from_dict(result_data["analysis"])
                            outline = Outline.from_dict(result_data["outline"])
                            new_text = agent.regenerate_chapter(
                                chapter_id=ch_id,
                                outline=outline,
                                analysis=analysis,
                                document_chapters=st.session_state.review_chapters,
                                llm_client=llm_client
                            )
                            st.session_state.review_chapters[ch_id] = new_text
                            st.success("重写完成！记得重新打包。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"重写失败: {e}")

    # 底部的重新打包引擎
    st.divider()
    if st.button("🚀 合并草稿并重新打包为最终交付文件", type="primary", use_container_width=True):
        with st.spinner("正在重新格式化全卷并打包..."):
            agent = SoftCopyrightAgent()
            analysis = AnalysisResult.from_dict(result_data["analysis"])
            outline = Outline.from_dict(result_data["outline"])
            
            code_files = []
            safe_title = analysis.title.replace(" ", "_").replace("/", "_").replace("\\", "_")
            source_dir = Path(result_data["output_dir"]) / f"{safe_title}_源代码"
            if source_dir.exists():
                for root, _, fs in os.walk(source_dir):
                    for f in fs:
                        p = Path(root) / f
                        rel_path = p.relative_to(source_dir).as_posix()
                        code_files.append(GeneratedFile(path=rel_path, content=p.read_text(encoding="utf-8")))
            
            new_run_result = agent.format_document(
                title=result_data["title"],
                analysis=analysis,
                outline=outline,
                document_chapters=st.session_state.review_chapters,
                code_files=code_files,
                config=config,
                generation_mode=result_data["generation_mode"]
            )
            st.session_state.last_result = new_run_result.to_dict()
            st.success("重打包完成！已覆盖输出件。")
            st.rerun()


def _render_file_browser(root: Path, *, title: str, editable: bool) -> None:
    import streamlit as st

    st.subheader(title)
    if not root.exists():
        st.info(f"{root} 尚不存在。")
        return
    st.write(f"目录：`{root}`")
    files = iter_display_files(root)
    if not files:
        st.info("没有可显示文件。")
        return
    if st.button(f"打包下载 {title}", key=f"download_zip_button_{title}"):
        st.session_state[f"zip_ready_{title}"] = True
    if st.session_state.get(f"zip_ready_{title}"):
        st.download_button(
            f"下载 {title}.zip",
            data=zip_directory(root),
            file_name=f"{title}.zip",
            mime="application/zip",
            key=f"download_zip_{title}",
        )
    for path in files[:200]:
        label = relative_label(path, root)
        with st.expander(label):
            if is_text_file(path):
                content = read_text(path)
                if editable:
                    edited = st.text_area("内容", value=content, height=320, key=f"browser_edit_{path}")
                    if st.button("保存修改", key=f"browser_save_{path}"):
                        write_text(path, edited)
                        st.success("已保存。")
                else:
                    st.code(content, language=language_for(path), line_numbers=True)
            else:
                st.write(f"二进制文件，大小 {path.stat().st_size} bytes")
                st.download_button("下载文件", data=path.read_bytes(), file_name=path.name, key=f"download_{path}")


def _render_file_editor(root: Path) -> None:
    import streamlit as st

    if not root.exists():
        st.info(f"{root} 尚不存在。")
        return
    files = [path for path in iter_display_files(root) if is_text_file(path)]
    if not files:
        st.info("没有可编辑文本文件。")
        return
    labels = [relative_label(path, root) for path in files]
    selected_label = st.selectbox("选择文件", labels)
    selected_path = files[labels.index(selected_label)]
    content = read_text(selected_path)
    edited = st.text_area("编辑内容", value=content, height=600, key=f"editor_{selected_path}")
    col1, col2 = st.columns([1, 4])
    if col1.button("保存", type="primary"):
        write_text(selected_path, edited)
        st.success(f"已保存：{selected_label}")
    with col2:
        st.download_button("下载当前文件", data=edited, file_name=selected_path.name, key=f"editor_download_{selected_path}")

def _render_history_preview() -> None:
    import streamlit as st

    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        st.info("暂未发现 `outputs` 目录。")
        return
        
    history = []
    for meta_file in outputs_dir.rglob("*_metadata.json"):
        try:
            content = meta_file.read_text(encoding="utf-8")
            data = json.loads(content)
            data["_mtime"] = meta_file.stat().st_mtime
            data["_meta_path"] = str(meta_file)
            history.append(data)
        except Exception:
            continue
            
    if not history:
        st.info("未找到任何历史生成记录（无 metadata.json 伴随）。")
        return

    history.sort(key=lambda d: d.get("_mtime", 0), reverse=True)
    
    st.subheader("加载历史记录")
    col1, col2 = st.columns([3, 1])
    options = [f"{d['title']} - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d['_mtime']))}" for d in history]
    selected_label = col1.selectbox("选择以前生成的内容", options)
    idx = options.index(selected_label)
    selected_data = history[idx]

    if col2.button("加载到结果区并作为当前任务", use_container_width=True):
        st.session_state.last_result = selected_data
        st.session_state.last_output_dir = Path(selected_data["_meta_path"]).parent
        st.success("已加载至会话，请点击【生成结果】选项卡查看或重新编辑。")

    st.subheader("Markdown 说明书预览")
    md_file = Path(selected_data["_meta_path"]).parent / f"{safe_filename(selected_data['title'])}_设计说明书.md"
    if md_file.exists():
        with st.expander("点击展开全文", expanded=False):
            st.markdown(md_file.read_text(encoding="utf-8"))
    else:
        st.warning("未找到对应的说明书 markdown 文件。")


def safe_filename(name: str) -> str:
    import re
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
