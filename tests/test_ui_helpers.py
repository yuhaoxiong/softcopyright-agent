import shutil
import unittest
import uuid
from pathlib import Path

from softcopyright_agent.ui import iter_display_files, is_text_file, language_for, read_text, write_text, zip_directory


class UIHelperTests(unittest.TestCase):
    def test_file_helpers_round_trip_and_zip(self):
        root = Path("outputs/test-tmp") / uuid.uuid4().hex
        try:
            (root / "src").mkdir(parents=True)
            py_file = root / "src" / "app.py"
            bin_file = root / "asset.bin"
            write_text(py_file, "print('ok')\n")
            bin_file.write_bytes(b"\x00\x01")

            files = iter_display_files(root)
            self.assertEqual(files[0], py_file)
            self.assertTrue(is_text_file(py_file))
            self.assertFalse(is_text_file(bin_file))
            self.assertEqual(language_for(py_file), "python")
            self.assertEqual(read_text(py_file), "print('ok')\n")
            self.assertGreater(len(zip_directory(root)), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
