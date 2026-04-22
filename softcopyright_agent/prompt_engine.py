"""Prompt template loading and rendering."""

from __future__ import annotations

from pathlib import Path
from string import Formatter


class PromptEngine:
    """Load prompt templates from package files and render simple placeholders."""

    def __init__(self, prompt_dir: Path | None = None, theme: str = "standard") -> None:
        self.prompt_dir = prompt_dir or Path(__file__).with_name("prompts")
        self.theme = theme

    def render(self, template_name: str, **context: object) -> str:
        p = self.prompt_dir / self.theme / template_name
        if not p.exists() and self.theme != "standard":
            p = self.prompt_dir / "standard" / template_name
        
        template = p.read_text(encoding="utf-8")
        safe_context = {key: str(value) for key, value in context.items()}
        expected = {field for _, field, _, _ in Formatter().parse(template) if field}
        missing = expected.difference(safe_context)
        if missing:
            raise KeyError(f"missing prompt context keys: {', '.join(sorted(missing))}")
        return template.format(**safe_context)
