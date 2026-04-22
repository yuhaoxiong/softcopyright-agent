"""Tests for prompt theme templates and rendering."""

import unittest
from pathlib import Path

from softcopyright_agent.prompt_engine import PromptEngine

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "softcopyright_agent" / "prompts"

# All themes that must have at least analyze/outline/write_chapter/generate_code
REQUIRED_THEMES = ["standard", "game", "algorithm", "frontend_only", "iot"]

# Templates that each theme must define (reduce_aigc uses standard fallback)
THEME_SPECIFIC_TEMPLATES = ["analyze.md", "outline.md", "write_chapter.md", "generate_code.md"]

# All templates including shared fallback
ALL_TEMPLATES = THEME_SPECIFIC_TEMPLATES + ["reduce_aigc.md"]


class TestPromptThemeFiles(unittest.TestCase):
    """Verify that all theme directories and template files exist."""

    def test_all_theme_directories_exist(self):
        for theme in REQUIRED_THEMES:
            theme_dir = PROMPTS_DIR / theme
            self.assertTrue(
                theme_dir.is_dir(),
                f"主题目录不存在: {theme_dir}",
            )

    def test_all_themes_have_required_templates(self):
        for theme in REQUIRED_THEMES:
            for tpl in THEME_SPECIFIC_TEMPLATES:
                tpl_path = PROMPTS_DIR / theme / tpl
                self.assertTrue(
                    tpl_path.is_file(),
                    f"模板文件缺失: {theme}/{tpl}",
                )

    def test_standard_has_reduce_aigc(self):
        self.assertTrue(
            (PROMPTS_DIR / "standard" / "reduce_aigc.md").is_file(),
            "standard/reduce_aigc.md 不存在",
        )

    def test_template_files_are_non_empty(self):
        for theme in REQUIRED_THEMES:
            for tpl in THEME_SPECIFIC_TEMPLATES:
                tpl_path = PROMPTS_DIR / theme / tpl
                content = tpl_path.read_text(encoding="utf-8")
                self.assertGreater(
                    len(content.strip()), 100,
                    f"模板内容过短: {theme}/{tpl} (仅 {len(content)} 字节)",
                )


class TestPromptRendering(unittest.TestCase):
    """Verify that PromptEngine can render all templates for all themes."""

    # Minimal context that satisfies all template placeholders
    ANALYZE_CTX = {
        "title": "测试软件系统V1.0",
        "project_type": "Web应用",
        "tech_stack": "默认",
        "database": "默认",
        "has_mobile": "False",
        "has_algo": "False",
    }
    OUTLINE_CTX = {
        "analysis": '{"keywords":["测试"]}',
        "target_words": "8000",
    }
    WRITE_CHAPTER_CTX = {
        "title": "测试软件系统V1.0",
        "chapter_title": "1. 软件概述",
        "target_words": "2000",
        "title_analysis": '{"keywords":["测试"]}',
        "outline": '{"chapters":[]}',
        "previous_chapters_summary": "无",
    }
    GENERATE_CODE_CTX = {
        "analysis": '{"keywords":["测试"]}',
        "outline": '{"chapters":[]}',
        "document_context": "测试上下文",
        "module": "module_01_test",
        "target_lines": "100",
    }
    REDUCE_AIGC_CTX = {
        "round_number": "1",
        "total_rounds": "2",
        "chapter_id": "chapter_1",
        "original_text": "测试原文内容",
    }

    TEMPLATE_CONTEXTS = {
        "analyze.md": ANALYZE_CTX,
        "outline.md": OUTLINE_CTX,
        "write_chapter.md": WRITE_CHAPTER_CTX,
        "generate_code.md": GENERATE_CODE_CTX,
        "reduce_aigc.md": REDUCE_AIGC_CTX,
    }

    def test_all_themes_render_successfully(self):
        for theme in REQUIRED_THEMES:
            engine = PromptEngine(theme=theme)
            for tpl, ctx in self.TEMPLATE_CONTEXTS.items():
                with self.subTest(theme=theme, template=tpl):
                    result = engine.render(tpl, **ctx)
                    self.assertIsInstance(result, str)
                    self.assertGreater(len(result), 50)

    def test_fallback_to_standard_for_reduce_aigc(self):
        """Non-standard themes should fall back to standard/reduce_aigc.md."""
        for theme in ["game", "algorithm", "frontend_only", "iot"]:
            engine = PromptEngine(theme=theme)
            result = engine.render("reduce_aigc.md", **self.REDUCE_AIGC_CTX)
            self.assertIn("改写", result)

    def test_theme_specific_content_differs(self):
        """Each theme's analyze.md should contain theme-specific keywords."""
        theme_markers = {
            "standard": "行业场景",
            "game": "游戏",
            "algorithm": "算法",
            "frontend_only": "前端",
            "iot": "工控",
        }
        for theme, marker in theme_markers.items():
            engine = PromptEngine(theme=theme)
            result = engine.render("analyze.md", **self.ANALYZE_CTX)
            self.assertIn(
                marker, result,
                f"{theme}/analyze.md 未包含主题标记词 '{marker}'",
            )


if __name__ == "__main__":
    unittest.main()
