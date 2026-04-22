import json
import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from softcopyright_agent.analyzer import TitleAnalyzer
from softcopyright_agent.code_generator import CodeGenerator
from softcopyright_agent.doc_writer import DocumentWriter
from softcopyright_agent.llm import DEFAULT_GROK_MODEL, GROK_BASE_URL, LLMSettings, create_llm_client, extract_json_object
from softcopyright_agent.models import GeneratedFile
from softcopyright_agent.outline_generator import OutlineGenerator
from softcopyright_agent.review import ReviewManager
from softcopyright_agent.utils.diagram_renderer import render_mermaid_to_png


class FakeLLM:
    provider_name = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system: str, user: str, temperature: float = 0.3) -> str:
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        if not self.responses:
            return "# LLM 章节\n\n这是由大模型生成的章节内容。"
        return self.responses.pop(0)


class LLMReviewTests(unittest.TestCase):
    def setUp(self):
        self.analysis = TitleAnalyzer().analyze("基于深度学习的智能问答系统 V1.0")

    def test_extract_json_object_accepts_fenced_json(self):
        data = extract_json_object("```json\n{\"ok\": true}\n```")
        self.assertEqual(data, {"ok": True})

    def test_grok_provider_uses_xai_defaults_and_keeps_provider_name(self):
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-key"}, clear=True):
            settings = LLMSettings.from_env("grok")
        client = create_llm_client(settings, required=True)

        self.assertEqual(settings.api_key, "xai-key")
        self.assertEqual(settings.base_url, GROK_BASE_URL)
        self.assertEqual(settings.model, DEFAULT_GROK_MODEL)
        self.assertEqual(client.provider_name, "grok")
        self.assertTrue(client.endpoint.endswith("/chat/completions"))

    def test_outline_document_and_code_can_use_llm(self):
        outline_payload = {
            "chapters": [
                {"id": "chapter_1", "title": "1. 引言", "target_words": 100, "sections": ["1.1 编写目的"]},
                {"id": "chapter_2", "title": "2. 软件总体设计", "target_words": 100, "sections": ["2.1 架构"]},
            ],
            "code_structure": {"services": ["module_01_user_service.py"]},
        }
        code_payload = [
            {
                "path": "services/module_01_user_service.py",
                "content": "class UserService:\n    def create_user(self):\n        return {'ok': True}\n",
            }
        ]
        fake = FakeLLM([json.dumps(outline_payload, ensure_ascii=False), "# LLM 章节一\n\n内容", "# LLM 章节二\n\n内容", json.dumps(code_payload, ensure_ascii=False)])
        self.analysis.core_modules = self.analysis.core_modules[:1]

        outline = OutlineGenerator().generate(self.analysis, 200, llm_client=fake)
        chapters = DocumentWriter().write(self.analysis, outline, llm_client=fake)
        files = CodeGenerator().generate(self.analysis, outline, 10, document_chapters=chapters, llm_client=fake)

        self.assertEqual(outline.chapters[0].title, "1. 引言")
        self.assertIn("LLM 章节一", chapters["chapter_1"])
        self.assertTrue(any(file.path == "services/module_01_user_service.py" for file in files))
        self.assertGreaterEqual(len(fake.calls), 4)

    def test_review_manager_round_trips_editable_files(self):
        outline = OutlineGenerator().generate(self.analysis, 1200)
        review_dir = Path("outputs/test-tmp") / uuid.uuid4().hex
        try:
            manager = ReviewManager(review_dir)
            reviewed_outline = manager.review_outline(outline)
            reviewed_document = manager.review_document({"chapter_1": "# 1. 引言\n\n内容"})
            reviewed_code = manager.review_code([])

            self.assertEqual(reviewed_outline.chapters[0].id, "chapter_1")
            self.assertIn("chapter_1", reviewed_document)
            self.assertEqual(reviewed_code, [])
        finally:
            shutil.rmtree(review_dir, ignore_errors=True)

    def test_review_manager_rejects_unsafe_generated_paths(self):
        review_dir = Path("outputs/test-tmp") / uuid.uuid4().hex
        try:
            manager = ReviewManager(review_dir)
            with self.assertRaises(ValueError):
                manager.review_code([GeneratedFile("../escape.py", "print('bad')\n")])
            self.assertFalse((review_dir.parent / "escape.py").exists())
        finally:
            shutil.rmtree(review_dir, ignore_errors=True)

    def test_remote_diagram_rendering_is_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                render_mermaid_to_png("graph TD; A-->B")

    def test_explicit_remote_diagram_setting_overrides_environment(self):
        with patch.dict(os.environ, {"SOFTCOPYRIGHT_ENABLE_REMOTE_DIAGRAMS": "1"}, clear=True):
            with self.assertRaises(RuntimeError):
                render_mermaid_to_png("graph TD; A-->B", allow_remote=False)


if __name__ == "__main__":
    unittest.main()
