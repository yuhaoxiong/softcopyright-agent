"""Soft copyright material generation agent."""

from .agent import SoftCopyrightAgent
from .models import AnalysisResult, GeneratedFile, Outline, RunConfig, RunResult

__all__ = [
    "AnalysisResult",
    "GeneratedFile",
    "Outline",
    "RunConfig",
    "RunResult",
    "SoftCopyrightAgent",
]

__version__ = "0.1.0"
