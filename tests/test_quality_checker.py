"""Tests for chapter quality self-checker (Agent Phase A core)."""

import unittest

from softcopyright_agent.models import Chapter
from softcopyright_agent.tools.quality_tool import ChapterQualityChecker


class TestWordCount(unittest.TestCase):
    """Word count dimension (0-25 points)."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_sufficient_words_scores_25(self):
        ch = Chapter(id="chapter_1", title="1. 软件概述", target_words=100, sections=[])
        content = "本系统采用分层架构设计，核心模块包括用户管理和数据处理。" * 8
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["word_count"], 25)

    def test_very_short_scores_zero(self):
        ch = Chapter(id="chapter_1", title="1. 软件概述", target_words=2000, sections=[])
        content = "简短。"
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["word_count"], 0)

    def test_moderate_shortage_scores_15(self):
        ch = Chapter(id="chapter_1", title="1. 软件概述", target_words=100, sections=[])
        # count_words = 65, 65/100 = 65% → hits >= 0.65 boundary → 15分
        content = "本系统采用分层架构设计说明。" * 5
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["word_count"], 15)


class TestDiagrams(unittest.TestCase):
    """Mermaid diagram dimension (0-25 points)."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_chapter_1_no_diagrams_needed(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "纯文字内容。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["diagrams"], 25)

    def test_chapter_2_missing_diagrams(self):
        ch = Chapter(id="chapter_2", title="2. 架构", target_words=50, sections=[])
        content = "无图表的架构描述。" * 10
        result = self.checker.check("chapter_2", content, ch)
        self.assertEqual(result.data["breakdown"]["diagrams"], 0)
        self.assertTrue(any("图表" in i for i in result.data["issues"]))

    def test_chapter_2_with_enough_diagrams(self):
        ch = Chapter(id="chapter_2", title="2. 架构", target_words=50, sections=[])
        diagram = "\n```mermaid\ngraph TD\nA-->B\n```\n"
        content = "架构说明。" * 5 + diagram * 2
        result = self.checker.check("chapter_2", content, ch)
        self.assertEqual(result.data["breakdown"]["diagrams"], 25)

    def test_chapter_4_partial_diagrams(self):
        ch = Chapter(id="chapter_4", title="4. 算法", target_words=50, sections=[])
        content = "算法说明。" * 5 + "\n```mermaid\nflowchart TD\nA-->B\n```\n"
        result = self.checker.check("chapter_4", content, ch)
        # Has 1 but needs 2
        self.assertEqual(result.data["breakdown"]["diagrams"], 15)


class TestDiagramNumbering(unittest.TestCase):
    """Diagram numbering dimension (0-15 points)."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_no_diagrams_full_score(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "纯文字。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["diagram_numbering"], 15)

    def test_diagrams_without_numbering(self):
        ch = Chapter(id="chapter_4", title="4. 算法", target_words=50, sections=[])
        content = "算法。" * 5 + "\n```mermaid\nflowchart TD\nA-->B\n```\n" * 2
        result = self.checker.check("chapter_4", content, ch)
        self.assertEqual(result.data["breakdown"]["diagram_numbering"], 0)

    def test_diagrams_with_proper_numbering(self):
        ch = Chapter(id="chapter_4", title="4. 算法", target_words=50, sections=[])
        block = "\n```mermaid\nflowchart TD\nA-->B\n```\n**图4-1 流程图**\n"
        block2 = "\n```mermaid\nflowchart TD\nC-->D\n```\n**图4-2 算法图**\n"
        content = "算法。" * 5 + block + block2
        result = self.checker.check("chapter_4", content, ch)
        self.assertEqual(result.data["breakdown"]["diagram_numbering"], 15)


class TestTables(unittest.TestCase):
    """Table presence dimension (0-15 points)."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_chapter_5_no_table(self):
        ch = Chapter(id="chapter_5", title="5. 数据结构", target_words=50, sections=[])
        content = "无表格的数据描述。" * 10
        result = self.checker.check("chapter_5", content, ch)
        self.assertEqual(result.data["breakdown"]["tables"], 0)

    def test_chapter_5_with_table(self):
        ch = Chapter(id="chapter_5", title="5. 数据结构", target_words=50, sections=[])
        content = "数据表。" * 5 + "\n| 字段 | 类型 | 描述 |\n|---|---|---|\n| id | INT | 主键 |\n"
        result = self.checker.check("chapter_5", content, ch)
        self.assertEqual(result.data["breakdown"]["tables"], 15)

    def test_chapter_3_no_table_required(self):
        ch = Chapter(id="chapter_3", title="3. 模块", target_words=50, sections=[])
        content = "模块描述。" * 10
        result = self.checker.check("chapter_3", content, ch)
        self.assertEqual(result.data["breakdown"]["tables"], 15)


class TestForbiddenPhrases(unittest.TestCase):
    """Forbidden phrase scan dimension (0-10 points)."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_clean_text_full_score(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "本系统采用分层架构设计。该模块负责数据处理与转发。" * 5
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["purity"], 10)

    def test_forbidden_phrases_detected(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "值得注意的是，本系统。综上所述，完成了设计。众所周知这很好。" * 3
        result = self.checker.check("chapter_1", content, ch)
        self.assertLess(result.data["breakdown"]["purity"], 10)
        self.assertTrue(any("短语" in i for i in result.data["issues"]))


class TestSections(unittest.TestCase):
    """Section structure dimension (0-10 points)."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_no_expected_sections_full_score(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "纯段落文字。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["sections"], 10)

    def test_missing_sections_penalized(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=["1.1 背景", "1.2 目标", "1.3 环境"])
        content = "没有子节的纯文字。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertLess(result.data["breakdown"]["sections"], 10)

    def test_with_enough_sections(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=["1.1 背景", "1.2 目标"])
        content = "## 1.1 背景\n内容。\n## 1.2 目标\n内容。\n"
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["breakdown"]["sections"], 10)


class TestOverallScore(unittest.TestCase):
    """Overall scoring and ToolResult behavior."""

    def setUp(self):
        self.checker = ChapterQualityChecker()

    def test_total_equals_sum_of_parts(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=100, sections=[])
        content = "本系统采用分层架构方案。" * 15
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.data["score"], sum(result.data["breakdown"].values()))

    def test_success_flag_matches_threshold(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "本系统设计说明如下。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertEqual(result.success, result.data["score"] >= 70)

    def test_observation_contains_issues_when_failing(self):
        ch = Chapter(id="chapter_2", title="2. 架构", target_words=2000, sections=["2.1 概述"])
        content = "极短。"
        result = self.checker.check("chapter_2", content, ch)
        self.assertFalse(result.success)
        self.assertIn("问题", result.observation)

    def test_observation_clean_when_passing(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "本系统设计说明如下。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertIn("通过", result.observation)

    def test_metrics_contains_quality_score(self):
        ch = Chapter(id="chapter_1", title="1. 概述", target_words=50, sections=[])
        content = "本系统设计。" * 10
        result = self.checker.check("chapter_1", content, ch)
        self.assertIn("quality_score", result.metrics)
        self.assertEqual(result.metrics["quality_score"], float(result.data["score"]))


if __name__ == "__main__":
    unittest.main()
