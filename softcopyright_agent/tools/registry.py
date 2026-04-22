"""Tool registry for the ReAct orchestrator.

Provides registration, discovery, and execution of named tools.
The orchestrator uses this to build its system prompt and dispatch actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .base import ToolResult


@dataclass(slots=True)
class ToolSpec:
    """A registered tool that the orchestrator can invoke."""

    name: str
    description: str
    parameters: dict[str, str]  # param_name -> description
    handler: Callable[..., ToolResult]


class ToolRegistry:
    """Central registry of available tools for the ReAct loop."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def format_for_prompt(self) -> str:
        """Format all tools as a numbered list for the LLM system prompt."""
        lines: list[str] = []
        for i, (name, spec) in enumerate(self._tools.items(), 1):
            params = ", ".join(f"{k}: {v}" for k, v in spec.parameters.items())
            lines.append(f"{i}. **{name}**({params})")
            lines.append(f"   {spec.description}")
        return "\n".join(lines)

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Look up and execute a named tool, returning a ToolResult."""
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(
                success=False,
                data={},
                observation=f"工具 '{name}' 不存在。可用工具: {', '.join(self._tools.keys())}",
            )
        try:
            return spec.handler(**kwargs)
        except Exception as exc:
            return ToolResult(
                success=False,
                data={"error": str(exc)},
                observation=f"工具 {name} 执行失败: {exc}",
            )
