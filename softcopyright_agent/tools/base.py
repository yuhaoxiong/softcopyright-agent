"""Base protocol for agent tools.

Defines the unified return type that all tools must produce,
enabling the agent orchestrator to uniformly process results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolResult:
    """Unified return value from any tool execution.

    Attributes:
        success: Whether the tool considers its output acceptable.
        data: Structured output data (tool-specific).
        observation: Human/LLM-readable summary of what happened.
        metrics: Optional numeric metrics for dashboarding.
    """

    success: bool
    data: dict[str, Any]
    observation: str
    metrics: dict[str, float] = field(default_factory=dict)
