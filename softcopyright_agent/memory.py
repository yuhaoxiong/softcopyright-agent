"""Agent working memory — tracks execution context for the ReAct loop.

Maintains a chronological log of thoughts, actions, and observations,
and provides context assembly for the LLM's next planning decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class MemoryEntry:
    """Single entry in the agent's working memory."""

    role: str  # "user", "thought", "action", "observation"
    content: str
    tool_name: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class AgentMemory:
    """Short-term working memory for the ReAct orchestrator.

    Provides context assembly for the LLM and execution traceability.
    """

    def __init__(self, max_context_chars: int = 12000) -> None:
        self.entries: list[MemoryEntry] = []
        self.max_context_chars = max_context_chars

    def add(self, role: str, content: str, tool_name: str | None = None) -> None:
        """Append an entry to the memory log."""
        self.entries.append(MemoryEntry(role=role, content=content, tool_name=tool_name))

    def get_context(self) -> str:
        """Assemble memory entries into an LLM-readable context string."""
        role_prefix = {
            "user": "[用户目标]",
            "thought": "[思考]",
            "action": "[动作]",
            "observation": "[观察结果]",
        }
        parts: list[str] = []
        for entry in self.entries:
            prefix = role_prefix.get(entry.role, f"[{entry.role}]")
            if entry.tool_name:
                prefix = f"[动作: {entry.tool_name}]"
            parts.append(f"{prefix} {entry.content}")

        full = "\n\n".join(parts)
        if len(full) > self.max_context_chars:
            full = "...(早期记录已省略)\n\n" + full[-self.max_context_chars :]
        return full

    def get_tools_called(self) -> list[str]:
        """Return ordered list of tool names that have been called."""
        return [e.tool_name for e in self.entries if e.role == "action" and e.tool_name]

    def get_execution_summary(self) -> str:
        """Return a concise summary of steps taken."""
        actions = [e for e in self.entries if e.role == "action"]
        observations = [e for e in self.entries if e.role == "observation"]
        lines: list[str] = []
        for i, a in enumerate(actions):
            obs = observations[i].content[:80] if i < len(observations) else "pending"
            lines.append(f"  {i + 1}. {a.tool_name}: {obs}")
        return f"已执行 {len(actions)} 步:\n" + "\n".join(lines) if lines else "尚无执行步骤"

    def clear(self) -> None:
        self.entries.clear()
