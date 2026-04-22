"""Tests for quality metrics assessment and AIGC deterministic reduction."""

import unittest

from softcopyright_agent.aigc_reducer import AIGCReducer
from softcopyright_agent.output_formatter import OutputFormatter
from softcopyright_agent.models import AnalysisResult, ModuleSpec, GeneratedFile


class TestAIGCReducerDeterministic(unittest.TestCase):
    """Snapshot tests for the deterministic text replacement pipeline."""

    def setUp(self):
        self.reducer = AIGCReducer()

    def test_removes_filler_phrases(self):
        text = "值得注意的是，系统很重要。需要指出的是，数据安全很重要。"
        result = self.reducer.reduce_text(text)
        self.assertNotIn("值得注意的是", result)
        self.assertNotIn("需要指出的是", result)

    def test_removes_all_empty_fillers(self):
        fillers = ["众所周知，", "毋庸置疑，", "显而易见，", "不言而喻，", "不可忽视的是，"]
        for filler in fillers:
            text = f"{filler}这是一段话。"
            result = self.reducer.reduce_text(text)
            self.assertNotIn(filler, result, f"应删除: {filler}")

    def test_replaces_summary_phrases(self):
        text = "总的来说，系统满足需求。综上所述，设计合理。"
        result = self.reducer.reduce_text(text)
        self.assertNotIn("总的来说", result)
        self.assertNotIn("综上所述", result)
        self.assertIn("从工程落地角度看", result)
        self.assertIn("按上述设计", result)

    def test_replaces_verbs(self):
        text = "系统采用了微服务架构，实现了高可用。"
        result = self.reducer.reduce_text(text)
        self.assertIn("选用了", result)
        self.assertIn("完成了", result)

    def test_context_replacements(self):
        text = "处理完成。系统进入下一步。"
        result = self.reducer.reduce_text(text)
        self.assertIn("在本系统中，", result)

    def test_preserves_non_empty_output(self):
        text = "值得注意的是，系统采用了先进的技术方案来确保数据安全。"
        result = self.reducer.reduce_text(text)
        self.assertTrue(len(result) > 0)

    def test_assess_reduction_metrics(self):
        original = "line one\nline two\nline three"
        reduced = "line one\nmodified two\nline three"
        metrics = AIGCReducer.assess_reduction(original, reduced)
        self.assertIn("change_ratio", metrics)
        self.assertIn("length_ratio", metrics)
        self.assertGreater(metrics["change_ratio"], 0.0)

    def test_reduce_document_fallback(self):
        chapters = {
            "ch1": "值得注意的是，这是第一章。",
            "ch2": "综上所述，这是第二章。",
        }
        result = self.reducer.reduce_document(chapters)
        self.assertEqual(len(result), 2)
        self.assertNotIn("值得注意的是", result["ch1"])
        self.assertNotIn("综上所述", result["ch2"])

    def test_idempotent_on_clean_text(self):
        """Text without any AI-isms should not be significantly altered."""
        text = "系统设计说明如下。"
        result = self.reducer.reduce_text(text)
        self.assertEqual(text, result)


class TestQualityMetrics(unittest.TestCase):
    """Tests for the 7-dimensional quality assessment logic."""

    def setUp(self):
        self.formatter = OutputFormatter()
        self.analysis = AnalysisResult(
            title="测试系统",
            normalized_title="测试系统",
            keywords=["测试"],
            tech_stack={"frontend": "Vue", "backend": "Flask", "database": "MySQL",
                        "ai_framework": "无", "deployment": "Docker"},
            business_domain="测试领域",
            core_modules=[
                ModuleSpec("用户管理模块", "module_01_user",
                           ["用户注册"], ["用户"], ["create_user"]),
                ModuleSpec("数据管理模块", "module_02_data",
                           ["数据处理"], ["数据"], ["create_data"]),
            ],
            architecture_style="分层架构",
            deployment_profile="单机部署",
        )
        self.default_doc = {"chapter_1": "系统设计包含认证、授权和安全防护、审计日志、鉴权机制。" * 50}

    def test_perfect_word_count_scores_20(self):
        metrics = self._assess(actual_words=9000, target_words=9000)
        self.assertEqual(metrics.word_count_score, 20)

    def test_half_word_count_scores_10(self):
        metrics = self._assess(actual_words=4500, target_words=9000)
        self.assertEqual(metrics.word_count_score, 10)

    def test_zero_word_count_scores_0(self):
        metrics = self._assess(actual_words=0, target_words=9000)
        self.assertEqual(metrics.word_count_score, 0)

    def test_perfect_line_count_scores_20(self):
        metrics = self._assess(source_lines=3000, target_lines=3000)
        self.assertEqual(metrics.line_count_score, 20)

    def test_total_score_is_sum(self):
        metrics = self._assess()
        expected = (
            metrics.word_count_score + metrics.line_count_score
            + metrics.module_consistency_score + metrics.doc_completeness_score
            + metrics.api_coverage_score + metrics.security_coverage_score
            + metrics.content_uniqueness_score
        )
        self.assertEqual(metrics.total_score, expected)

    def test_module_coverage_with_matching_files(self):
        code_files = [
            GeneratedFile("api/module_01_user_api.py", "# user api\n"),
            GeneratedFile("api/module_02_data_api.py", "# data api\n"),
        ]
        metrics = self._assess(code_files=code_files)
        self.assertEqual(metrics.module_consistency_score, 15)

    def test_module_coverage_with_no_matching_files(self):
        code_files = [GeneratedFile("README.md", "# readme\n")]
        metrics = self._assess(code_files=code_files)
        self.assertEqual(metrics.module_consistency_score, 0)

    def test_security_score_dynamic(self):
        doc = {"ch1": "系统具备认证、授权、加密、权限、安全五大安全措施。"}
        metrics = self._assess(document_chapters=doc)
        self.assertEqual(metrics.security_coverage_score, 10)

    def test_security_score_low_when_no_keywords(self):
        doc = {"ch1": "这是一段普通的技术文档，不含安全相关术语。"}
        metrics = self._assess(document_chapters=doc)
        self.assertLess(metrics.security_coverage_score, 5)

    def test_uniqueness_score_penalizes_duplicate_chapters(self):
        duplicate_text = "完全相同的一段设计文档内容。" * 30
        doc = {"ch1": duplicate_text, "ch2": duplicate_text}
        metrics = self._assess(document_chapters=doc)
        self.assertLessEqual(metrics.content_uniqueness_score, 5)

    def test_uniqueness_score_rewards_unique_chapters(self):
        doc = {
            "ch1": "用户管理模块负责注册、登录和权限控制。" * 20,
            "ch2": "数据库设计采用MySQL存储，Redis缓存热点查询。" * 20,
        }
        metrics = self._assess(document_chapters=doc)
        self.assertGreaterEqual(metrics.content_uniqueness_score, 7)

    def test_api_coverage_detects_api_path(self):
        code_files = [GeneratedFile("api/user_api.py", "# api\n")]
        metrics = self._assess(code_files=code_files)
        self.assertEqual(metrics.api_coverage_score, 10)

    def test_api_coverage_fallback_without_api(self):
        code_files = [GeneratedFile("models/user.py", "# model\n")]
        metrics = self._assess(code_files=code_files)
        self.assertEqual(metrics.api_coverage_score, 5)

    def _assess(self, *, actual_words=9000, target_words=9000,
                source_lines=3000, target_lines=3000,
                code_files=None, document_chapters=None):
        if code_files is None:
            code_files = [
                GeneratedFile("api/module_01_user_api.py",
                              "\n".join(["# line"] * 100)),
                GeneratedFile("api/module_02_data_api.py",
                              "\n".join(["# line"] * 100)),
            ]
        word_counts = {"total": actual_words, "chapter_1": actual_words}
        doc = document_chapters or self.default_doc
        return self.formatter._assess_quality(
            analysis=self.analysis,
            code_files=code_files,
            word_counts=word_counts,
            target_doc_words=target_words,
            source_lines=source_lines,
            target_code_lines=target_lines,
            document_chapters=doc,
        )


if __name__ == "__main__":
    unittest.main()
