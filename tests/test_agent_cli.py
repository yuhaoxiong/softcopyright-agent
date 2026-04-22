import json
import subprocess
import sys
import unittest
import uuid
import shutil
from pathlib import Path

from softcopyright_agent import SoftCopyrightAgent
from softcopyright_agent.models import RunConfig


class AgentCliTests(unittest.TestCase):
    def test_agent_end_to_end_low_threshold(self):
        output_dir = Path("outputs/test-tmp") / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = SoftCopyrightAgent().run(
                "基于深度学习的智能问答系统 V1.0",
                RunConfig(output_dir=output_dir, target_doc_words=1200, target_code_lines=350, create_docx=False),
            )

            self.assertGreaterEqual(result.document_words, 1000)
            self.assertGreaterEqual(result.source_lines, 350)
            self.assertIsNotNone(result.quality_metrics)
            self.assertTrue(result.files["markdown"].exists())
            self.assertTrue(result.files["source_dir"].exists())
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_cli_outputs_json_summary(self):
        output_dir = Path("outputs/test-tmp") / uuid.uuid4().hex
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "softcopyright_agent",
                    "基于深度学习的智能问答系统 V1.0",
                    "--output",
                    str(output_dir),
                    "--doc-words",
                    "1200",
                    "--code-lines",
                    "350",
                    "--no-docx",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(completed.stdout)
            self.assertGreaterEqual(data["document_words"], 1000)
            self.assertGreaterEqual(data["source_lines"], 350)
            self.assertIsNotNone(data["quality_metrics"])
            self.assertTrue(Path(data["files"]["markdown"]).exists())
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
