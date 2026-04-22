import unittest
import uuid
import shutil
from pathlib import Path

from softcopyright_agent.aigc_reducer import AIGCReducer
from softcopyright_agent.analyzer import TitleAnalyzer
from softcopyright_agent.code_generator import CodeGenerator
from softcopyright_agent.doc_writer import DocumentWriter
from softcopyright_agent.models import GeneratedFile
from softcopyright_agent.outline_generator import OutlineGenerator
from softcopyright_agent.output_formatter import OutputFormatter
from softcopyright_agent.utils.word_counter import count_words


class GenerationComponentTests(unittest.TestCase):
    def setUp(self):
        self.analysis = TitleAnalyzer().analyze("基于深度学习的智能问答系统 V1.0")
        self.outline = OutlineGenerator().generate(self.analysis, target_total_words=1200)

    def test_document_writer_reaches_chapter_budget(self):
        chapters = DocumentWriter().write(self.analysis, self.outline)

        self.assertEqual(set(chapters), {chapter.id for chapter in self.outline.chapters})
        total_words = sum(count_words(content) for content in chapters.values())
        self.assertGreaterEqual(total_words, 1000)
        self.assertIn("智能问答引擎模块", chapters["chapter_3"])

    def test_aigc_reducer_rewrites_template_phrases(self):
        text = "值得注意的是，系统采用分层架构。总的来说，能够确保流程完整。"
        reduced = AIGCReducer().reduce_text(text)

        self.assertNotIn("值得注意的是", reduced)
        self.assertIn("选用", reduced)
        self.assertIn("从工程落地角度看", reduced)

    def test_code_generator_reaches_target_lines(self):
        files = CodeGenerator().generate(self.analysis, self.outline, target_lines=350)

        self.assertGreaterEqual(sum(file.line_count for file in files), 350)
        paths = {file.path for file in files}
        self.assertIn("app.py", paths)
        self.assertIn("services/module_02_qa_engine_service.py", paths)

    def test_output_formatter_writes_expected_artifacts(self):
        chapters = AIGCReducer().reduce_document(DocumentWriter().write(self.analysis, self.outline))
        files = CodeGenerator().generate(self.analysis, self.outline, target_lines=350)
        output_dir = Path("outputs/test-tmp") / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = OutputFormatter().format(
                title=self.analysis.title,
                output_dir=output_dir,
                analysis=self.analysis,
                outline=self.outline,
                document_chapters=chapters,
                code_files=files,
                target_doc_words=1200,
                target_code_lines=350,
                create_docx=True,
            )

            self.assertTrue(result["markdown"].exists())
            self.assertTrue(result["docx"].exists())
            self.assertTrue(result["report"].exists())
            self.assertTrue(result["metadata"].exists())
            self.assertTrue((result["source_dir"] / "app.py").exists())
            self.assertGreaterEqual(result["source_lines"], 350)
            self.assertIsNotNone(result["quality_metrics"])
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_output_formatter_rejects_unsafe_generated_paths(self):
        chapters = DocumentWriter().write(self.analysis, self.outline)
        output_dir = Path("outputs/test-tmp") / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        escape_path = output_dir.parent / "escape.py"
        try:
            with self.assertRaises(ValueError):
                OutputFormatter().format(
                    title=self.analysis.title,
                    output_dir=output_dir,
                    analysis=self.analysis,
                    outline=self.outline,
                    document_chapters=chapters,
                    code_files=[GeneratedFile("../escape.py", "print('bad')\n")],
                    target_doc_words=1200,
                    target_code_lines=350,
                    create_docx=False,
                )
            self.assertFalse(escape_path.exists())
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
