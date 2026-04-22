import unittest

from softcopyright_agent.analyzer import TitleAnalyzer
from softcopyright_agent.outline_generator import OutlineGenerator


class AnalyzerOutlineTests(unittest.TestCase):
    def test_analyzer_extracts_ai_qa_modules(self):
        analysis = TitleAnalyzer().analyze("基于深度学习的智能问答系统 V1.0")

        self.assertEqual(analysis.business_domain, "智能客服/知识问答")
        self.assertIn("PyTorch", analysis.tech_stack["ai_framework"])
        module_names = [module.name for module in analysis.core_modules]
        self.assertIn("智能问答引擎模块", module_names)
        self.assertGreaterEqual(len(analysis.core_modules), 5)
        self.assertLessEqual(len(analysis.core_modules), 8)

    def test_outline_keeps_module_sections_and_code_structure_aligned(self):
        analysis = TitleAnalyzer().analyze("基于深度学习的智能问答系统 V1.0")
        outline = OutlineGenerator().generate(analysis, target_total_words=1200)

        chapter_3 = next(chapter for chapter in outline.chapters if chapter.id == "chapter_3")
        for module in analysis.core_modules:
            self.assertIn(f"models/{module.slug}.py", [f"models/{file}" for file in outline.code_structure["models"]])
            self.assertTrue(any(module.name in section for section in chapter_3.sections))

        self.assertEqual(len(outline.chapters), 7)
        self.assertEqual(sum(chapter.target_words for chapter in outline.chapters), 1200)


if __name__ == "__main__":
    unittest.main()
