"""Human review checkpoints for generated drafts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .models import GeneratedFile, Outline
from .utils.file_utils import ensure_dir, safe_child_path


class ReviewManager:
    """Persist editable drafts and optionally pause for human changes."""

    def __init__(self, review_dir: Path, *, interactive: bool = False) -> None:
        self.review_dir = ensure_dir(review_dir)
        self.interactive = interactive

    def review_outline(self, outline: Outline) -> Outline:
        path = self.review_dir / "01_outline.json"
        path.write_text(json.dumps(outline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._pause("目录草稿已写入", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return Outline.from_dict(data)

    def review_document(self, chapters: dict[str, str]) -> dict[str, str]:
        document_dir = ensure_dir(self.review_dir / "02_document")
        for chapter_id, content in chapters.items():
            (document_dir / f"{chapter_id}.md").write_text(content, encoding="utf-8")
        self._pause("说明书章节草稿已写入", document_dir)
        reviewed: dict[str, str] = {}
        for path in sorted(document_dir.glob("*.md")):
            reviewed[path.stem] = path.read_text(encoding="utf-8")
        return reviewed

    def review_code(self, files: list[GeneratedFile]) -> list[GeneratedFile]:
        code_dir = self.review_dir / "03_code"
        if code_dir.exists():
            shutil.rmtree(code_dir)
        ensure_dir(code_dir)
        for generated in files:
            target = safe_child_path(code_dir, generated.path)
            ensure_dir(target.parent)
            target.write_text(generated.content, encoding="utf-8")
        self._pause("源代码草稿已写入", code_dir)
        reviewed: list[GeneratedFile] = []
        for path in sorted(file for file in code_dir.rglob("*") if file.is_file()):
            reviewed.append(GeneratedFile(path.relative_to(code_dir).as_posix(), path.read_text(encoding="utf-8")))
        return reviewed

    def _pause(self, message: str, path: Path) -> None:
        if not self.interactive:
            return
        print(f"{message}: {path}")
        input("请完成审查/修改后按 Enter 继续...")
