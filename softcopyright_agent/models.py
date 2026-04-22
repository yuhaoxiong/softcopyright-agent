"""Shared data structures for the soft copyright generation pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ModuleSpec:
    """A business module shared by document and code generation."""

    name: str
    slug: str
    responsibilities: list[str]
    entities: list[str]
    interfaces: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModuleSpec":
        return cls(
            name=str(data["name"]),
            slug=str(data["slug"]),
            responsibilities=list(data.get("responsibilities", [])),
            entities=list(data.get("entities", [])),
            interfaces=list(data.get("interfaces", [])),
        )


@dataclass(slots=True)
class AnalysisResult:
    """Structured result produced from the user's soft copyright title."""

    title: str
    normalized_title: str
    keywords: list[str]
    tech_stack: dict[str, str]
    business_domain: str
    core_modules: list[ModuleSpec]
    architecture_style: str
    deployment_profile: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResult":
        return cls(
            title=str(data.get("title", "")),
            normalized_title=str(data.get("normalized_title", "")),
            keywords=list(data.get("keywords", [])),
            tech_stack=dict(data.get("tech_stack", {})),
            business_domain=str(data.get("business_domain", "")),
            core_modules=[ModuleSpec.from_dict(m) for m in data.get("core_modules", [])],
            architecture_style=str(data.get("architecture_style", "")),
            deployment_profile=str(data.get("deployment_profile", "")),
        )


@dataclass(slots=True)
class Chapter:
    """A design document chapter with target word budget."""

    id: str
    title: str
    target_words: int
    sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chapter":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            target_words=int(data["target_words"]),
            sections=list(data.get("sections", [])),
        )


@dataclass(slots=True)
class Outline:
    """Document outline and code structure plan."""

    chapters: list[Chapter]
    code_structure: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "code_structure": self.code_structure,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Outline":
        return cls(
            chapters=[Chapter.from_dict(chapter) for chapter in data.get("chapters", [])],
            code_structure={str(key): list(value) for key, value in data.get("code_structure", {}).items()},
        )


@dataclass(slots=True)
class GeneratedFile:
    """A generated source file that will be written to the output directory."""

    path: str
    content: str

    @property
    def line_count(self) -> int:
        return len(self.content.splitlines())

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line_count": self.line_count}


@dataclass(slots=True)
class RunConfig:
    """Runtime configuration for one agent run."""

    output_dir: Path = Path("outputs/generated")
    target_doc_words: int = 9000
    target_code_lines: int = 3000
    project_type: str = "默认模式"
    tech_stack: str = "默认"
    database: str = "默认"
    has_algo: bool = False
    has_mobile: bool = False
    create_docx: bool = True
    enable_remote_diagrams: bool = False
    confirm_outline: bool = False
    llm_provider: str = "auto"
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_required: bool = False
    aigc_rounds: int = 1
    interactive_review: bool = False
    review_dir: Path | None = None
    theme: str = "standard"


@dataclass(slots=True)
class QualityMetrics:
    """Assessment of generated material quality (7-Dim Radar)."""

    word_count_score: int
    line_count_score: int
    module_consistency_score: int
    doc_completeness_score: int
    api_coverage_score: int
    security_coverage_score: int
    content_uniqueness_score: int
    total_score: int
    assessment_detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunResult:
    """Final result of a generation run."""

    title: str
    output_dir: Path
    analysis: AnalysisResult
    outline: Outline
    document_words: int
    source_lines: int
    files: dict[str, Path]
    document_chapters: dict[str, str] | None = None
    generation_mode: str = "fallback"
    quality_metrics: QualityMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "output_dir": str(self.output_dir),
            "analysis": self.analysis.to_dict(),
            "outline": self.outline.to_dict(),
            "document_words": self.document_words,
            "source_lines": self.source_lines,
            "document_chapters": self.document_chapters,
            "generation_mode": self.generation_mode,
            "quality_metrics": self.quality_metrics.to_dict() if self.quality_metrics else None,
            "files": {key: str(value) for key, value in self.files.items()},
        }
