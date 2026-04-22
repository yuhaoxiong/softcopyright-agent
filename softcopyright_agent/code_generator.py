"""Phase 4: source code material generation."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from .llm import LLMClient, extract_json_object
from .models import AnalysisResult, GeneratedFile, Outline, ModuleSpec
from .prompt_engine import PromptEngine
from .utils.file_utils import safe_relative_path


class CodeGenerator:
    """Generate source-code material aligned to the document modules."""

    def generate(
        self,
        analysis: AnalysisResult,
        outline: Outline,
        target_lines: int = 3000,
        *,
        document_chapters: dict[str, str] | None = None,
        llm_client: LLMClient | None = None,
        prompt_engine: PromptEngine | None = None,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> list[GeneratedFile]:
        if llm_client is not None:
            return self._generate_with_llm(
                analysis,
                outline,
                target_lines,
                document_chapters=document_chapters or {},
                llm_client=llm_client,
                prompt_engine=prompt_engine or PromptEngine(),
                progress_callback=progress_callback,
            )
        return self._fallback_generate(analysis, outline, target_lines, progress_callback=progress_callback)

    def _generate_with_llm(
        self,
        analysis: AnalysisResult,
        outline: Outline,
        target_lines: int,
        *,
        document_chapters: dict[str, str],
        llm_client: LLMClient,
        prompt_engine: PromptEngine,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> list[GeneratedFile]:
        files: list[GeneratedFile] = [
            GeneratedFile("README.md", self._readme_md(analysis, outline)),
            GeneratedFile("tests/test_generated_contract.py", self._contract_test_py(analysis)),
        ]
        per_module_target = max(120, target_lines // max(1, len(analysis.core_modules)))
        document_context = "\n\n".join(document_chapters.values())[:12000]
        total_modules = len(analysis.core_modules)

        def _gen_one_module(module):
            prompt = prompt_engine.render(
                "generate_code.md",
                analysis=json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
                outline=json.dumps(outline.to_dict(), ensure_ascii=False, indent=2),
                document_context=document_context,
                module=json.dumps(module.to_dict(), ensure_ascii=False, indent=2),
                target_lines=per_module_target,
            )
            response = llm_client.generate(
                system="你是高级 Python 后端工程师。只输出 JSON 文件数组，每个文件必须是完整可读的源码。",
                user=prompt,
                temperature=0.25,
            )
            return module.name, self._parse_generated_files(response)

        with ThreadPoolExecutor(max_workers=min(4, total_modules)) as executor:
            futures = {
                executor.submit(_gen_one_module, module): module
                for module in analysis.core_modules
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                module_name, module_files = future.result()
                files.extend(module_files)
                if progress_callback:
                    progress_callback(
                        "源代码生成",
                        0.8 + 0.15 * (completed / max(total_modules, 1)),
                        f"完成模块代码：{module_name} ({completed}/{total_modules})",
                    )

        return self._deduplicate_files(files)

    def _fallback_generate(self, analysis: AnalysisResult, outline: Outline, target_lines: int = 3000, progress_callback: Callable[[str, float, str], None] | None = None) -> list[GeneratedFile]:
        files: list[GeneratedFile] = [
            GeneratedFile("app.py", self._app_py(analysis)),
            GeneratedFile("config/__init__.py", '"""Configuration package."""\n'),
            GeneratedFile("config/settings.py", self._settings_py(analysis)),
            GeneratedFile("config/database.py", self._database_py(analysis)),
            GeneratedFile("models/__init__.py", '"""Generated model package."""\n'),
            GeneratedFile("models/base.py", self._base_model_py()),
            GeneratedFile("utils/__init__.py", '"""Generated utility package."""\n'),
            GeneratedFile("utils/auth.py", self._auth_py()),
            GeneratedFile("utils/logger.py", self._logger_py()),
            GeneratedFile("utils/validators.py", self._validators_py()),
            GeneratedFile("README.md", self._readme_md(analysis, outline)),
            GeneratedFile("tests/__init__.py", ""),
            GeneratedFile("tests/test_generated_contract.py", self._contract_test_py(analysis)),
        ]

        per_file_target = max(80, target_lines // max(1, len(analysis.core_modules) * 3))
        total_modules = len(analysis.core_modules)
        for i, module in enumerate(analysis.core_modules):
            if progress_callback:
                progress_callback("源代码生成", 0.8 + 0.15 * (i / max(total_modules, 1)), f"生成模块代码：{module.name} ({i+1}/{total_modules})")
            files.append(GeneratedFile(f"models/{module.slug}.py", self._module_model_py(module, per_file_target)))
            files.append(GeneratedFile(f"services/{module.slug}_service.py", self._module_service_py(module, per_file_target)))
            files.append(GeneratedFile(f"api/{module.slug}_api.py", self._module_api_py(module, per_file_target)))

        current_lines = sum(file.line_count for file in files)
        if current_lines < target_lines:
            files.append(GeneratedFile("services/extension_rules.py", self._extension_rules_py(analysis, target_lines - current_lines + 20)))
        return files

    def _parse_generated_files(self, response: str) -> list[GeneratedFile]:
        data = extract_json_object(response)
        if not isinstance(data, list):
            raise ValueError("code generation response must be a JSON array")
        files: list[GeneratedFile] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            raw_path = str(item.get("path", "")).strip().replace("\\", "/")
            content = str(item.get("content", "")).rstrip() + "\n"
            if raw_path and content.strip():
                path = safe_relative_path(raw_path).as_posix()
                files.append(GeneratedFile(path, content))
        if not files:
            raise ValueError("code generation response did not include files")
        return files

    def _deduplicate_files(self, files: list[GeneratedFile]) -> list[GeneratedFile]:
        merged: dict[str, GeneratedFile] = {}
        for file in files:
            merged[file.path] = file
        return list(merged.values())

    def _app_py(self, analysis: AnalysisResult) -> str:
        routes = "\n".join(f"    register_blueprint(app, '{module.slug}')  # {module.name}" for module in analysis.core_modules)
        return f'''"""Application entry for {analysis.title}."""

from config.settings import Settings


def create_app(settings: Settings | None = None):
    """Create and configure the Flask application."""

    settings = settings or Settings()
    app = {{"name": settings.APP_NAME, "blueprints": []}}
{routes}
    return app


def register_blueprint(app, module_slug: str):
    """Register a generated module endpoint group."""

    app["blueprints"].append(f"/api/{{module_slug}}")
    return app


if __name__ == "__main__":
    application = create_app()
    print(f"started {{application['name']}} with {{len(application['blueprints'])}} modules")
'''

    def _settings_py(self, analysis: AnalysisResult) -> str:
        return f'''"""Runtime settings for generated soft copyright source."""

from dataclasses import dataclass


@dataclass
class Settings:
    """Centralized application settings."""

    APP_NAME: str = "{analysis.title}"
    BUSINESS_DOMAIN: str = "{analysis.business_domain}"
    DATABASE_URL: str = "mysql+pymysql://softcopyright:change-me@127.0.0.1:3306/softcopyright"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    SECRET_KEY: str = "replace-in-production"
    PAGE_SIZE: int = 20
    REQUEST_TIMEOUT_SECONDS: int = 15
    AUDIT_ENABLED: bool = True
'''

    def _database_py(self, analysis: AnalysisResult) -> str:
        table_lines = "\n".join(f'    "{module.slug}": "{module.slug.replace("module_", "biz_")}",' for module in analysis.core_modules)
        return f'''"""Database naming and connection helpers."""

TABLES = {{
{table_lines}
}}


class DatabaseSession:
    """Small session facade used by generated services."""

    def __init__(self):
        self.operations = []

    def add(self, table: str, payload: dict):
        self.operations.append(("add", table, payload))
        return {{"table": table, "payload": payload, "operation": "add"}}

    def update(self, table: str, record_id: str, payload: dict):
        self.operations.append(("update", table, record_id, payload))
        return {{"table": table, "record_id": record_id, "payload": payload, "operation": "update"}}

    def query(self, table: str, filters: dict):
        self.operations.append(("query", table, filters))
        return []

    def commit(self):
        return len(self.operations)
'''

    def _base_model_py(self) -> str:
        return '''"""Base model primitives."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BaseRecord:
    """Common fields for generated business records."""

    id: str
    name: str
    status: str = "active"
    owner_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def mark_updated(self):
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
'''

    def _auth_py(self) -> str:
        return '''"""Authentication helpers."""

import hashlib
import hmac


def hash_token(raw_token: str, secret: str) -> str:
    """Hash a token for storage or comparison."""

    return hmac.new(secret.encode("utf-8"), raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_permission(user: dict, permission: str) -> bool:
    """Check whether a user owns a named permission."""

    permissions = set(user.get("permissions", []))
    return "admin" in permissions or permission in permissions
'''

    def _logger_py(self) -> str:
        return '''"""Audit logging helpers."""

from datetime import datetime


def audit_event(operator_id: str, action: str, target: str, payload: dict | None = None) -> dict:
    """Build a normalized audit event."""

    return {
        "operator_id": operator_id,
        "action": action,
        "target": target,
        "payload": payload or {},
        "created_at": datetime.utcnow().isoformat(),
    }
'''

    def _validators_py(self) -> str:
        return '''"""Validation helpers."""


def require_fields(payload: dict, fields: list[str]) -> None:
    """Raise ValueError when required fields are missing."""

    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")


def normalize_page(page: int, page_size: int) -> tuple[int, int]:
    """Normalize pagination parameters."""

    return max(1, int(page)), min(100, max(1, int(page_size)))
'''

    def _module_model_py(self, module: ModuleSpec, target_lines: int) -> str:
        class_name = self._class_name(module.slug, "Record")
        lines = [
            f'"""Data model for {module.name}."""',
            "",
            "from dataclasses import dataclass, field",
            "from datetime import datetime",
            "from models.base import BaseRecord",
            "",
            "",
            "@dataclass",
            f"class {class_name}(BaseRecord):",
            f'    """Persistent record used by {module.name}."""',
            "",
            "    description: str = \"\"",
            "    tags: list[str] = field(default_factory=list)",
            "    metadata: dict = field(default_factory=dict)",
            "",
            "    def validate(self) -> None:",
            "        \"\"\"Validate business fields before persistence.\"\"\"",
            "        if not self.id:",
            "            raise ValueError(\"id is required\")",
            "        if not self.name:",
            "            raise ValueError(\"name is required\")",
            "",
            "    def apply_metadata(self, key: str, value):",
            "        \"\"\"Attach a metadata value and update timestamp.\"\"\"",
            "        self.metadata[key] = value",
            "        self.updated_at = datetime.utcnow()",
            "",
        ]
        return self._pad_with_methods(lines, target_lines, f"{class_name}FieldRule")

    def _module_service_py(self, module: ModuleSpec, target_lines: int) -> str:
        class_name = self._class_name(module.slug, "Service")
        table = module.slug.replace("module_", "biz_")
        lines = [
            f'"""Business service for {module.name}."""',
            "",
            "from config.database import DatabaseSession",
            "from utils.logger import audit_event",
            "from utils.validators import normalize_page, require_fields",
            "",
            "",
            f"class {class_name}:",
            f'    """Coordinate validation, persistence, and audit logic for {module.name}."""',
            "",
            "    def __init__(self, session: DatabaseSession | None = None):",
            "        self.session = session or DatabaseSession()",
            f"        self.table_name = \"{table}\"",
            "",
            "    def create(self, payload: dict, operator_id: str) -> dict:",
            "        \"\"\"Create one business record.\"\"\"",
            "        require_fields(payload, [\"id\", \"name\"])",
            "        result = self.session.add(self.table_name, payload)",
            f"        result[\"audit\"] = audit_event(operator_id, \"create\", \"{module.name}\", payload)",
            "        self.session.commit()",
            "        return result",
            "",
            "    def update(self, record_id: str, payload: dict, operator_id: str) -> dict:",
            "        \"\"\"Update one business record.\"\"\"",
            "        require_fields({\"record_id\": record_id}, [\"record_id\"])",
            "        result = self.session.update(self.table_name, record_id, payload)",
            f"        result[\"audit\"] = audit_event(operator_id, \"update\", \"{module.name}\", payload)",
            "        self.session.commit()",
            "        return result",
            "",
            "    def query(self, filters: dict, page: int = 1, page_size: int = 20) -> dict:",
            "        \"\"\"Query records with normalized pagination.\"\"\"",
            "        page, page_size = normalize_page(page, page_size)",
            "        rows = self.session.query(self.table_name, filters)",
            "        return {\"page\": page, \"page_size\": page_size, \"items\": rows}",
            "",
        ]
        for index, responsibility in enumerate(module.responsibilities, start=1):
            lines.extend(
                [
                    f"    def handle_responsibility_{index:02d}(self, payload: dict, operator_id: str) -> dict:",
                    f'        """Execute responsibility: {responsibility}."""',
                    "        require_fields(payload, [\"id\", \"name\"])",
                    f"        payload[\"responsibility\"] = \"{responsibility}\"",
                    "        return self.create(payload, operator_id)",
                    "",
                ]
            )
        return self._pad_with_methods(lines, target_lines, f"{class_name}Rule")

    def _module_api_py(self, module: ModuleSpec, target_lines: int) -> str:
        class_name = self._class_name(module.slug, "Api")
        service_class = self._class_name(module.slug, "Service")
        lines = [
            f'"""API endpoints for {module.name}."""',
            "",
            f"from services.{module.slug}_service import {service_class}",
            "",
            "",
            f"class {class_name}:",
            f'    """Request handlers for {module.name}."""',
            "",
            "    def __init__(self, service=None):",
            f"        self.service = service or {service_class}()",
            "",
            "    def save(self, request: dict) -> dict:",
            "        \"\"\"Validate request payload and save a record.\"\"\"",
            "        payload = request.get(\"json\", {})",
            "        operator_id = request.get(\"operator_id\", \"system\")",
            "        if payload.get(\"id\") and request.get(\"method\") == \"PUT\":",
            "            return self.service.update(payload[\"id\"], payload, operator_id)",
            "        return self.service.create(payload, operator_id)",
            "",
            "    def query(self, request: dict) -> dict:",
            "        \"\"\"Query records from request parameters.\"\"\"",
            "        return self.service.query(request.get(\"filters\", {}), request.get(\"page\", 1), request.get(\"page_size\", 20))",
            "",
        ]
        for interface in module.interfaces:
            lines.extend(
                [
                    f"    def {interface}(self, request: dict) -> dict:",
                    f'        """Adapter for interface {interface}."""',
                    "        if interface_payload := request.get(\"json\"):",
                    "            return self.save({\"json\": interface_payload, \"operator_id\": request.get(\"operator_id\", \"system\")})",
                    "        return self.query(request)",
                    "",
                ]
            )
        return self._pad_with_methods(lines, target_lines, f"{class_name}Endpoint")

    def _extension_rules_py(self, analysis: AnalysisResult, target_lines: int) -> str:
        lines = ['"""Extended business rules used to satisfy source material completeness."""', "", "def build_rule_catalog() -> list[dict]:", '    """Return generated validation and processing rules."""', "    rules = []"]
        index = 1
        while len(lines) < target_lines - 2:
            module = analysis.core_modules[index % len(analysis.core_modules)]
            lines.extend(
                [
                    "    rules.append({",
                    f"        \"code\": \"RULE_{index:04d}\",",
                    f"        \"module\": \"{module.name}\",",
                    f"        \"description\": \"校验{module.name}在场景{index}下的数据完整性和审计要求\",",
                    "        \"enabled\": True,",
                    "    })",
                ]
            )
            index += 1
        lines.extend(["    return rules", ""])
        return "\n".join(lines)

    def _readme_md(self, analysis: AnalysisResult, outline: Outline) -> str:
        modules = "\n".join(f"- {module.name}: {', '.join(module.responsibilities)}" for module in analysis.core_modules)
        structure = "\n".join(f"- {folder}: {', '.join(files)}" for folder, files in outline.code_structure.items())
        return f"""# {analysis.title} 源代码说明

## 模块
{modules}

## 目录结构
{structure}

## 运行说明
该代码为软件著作权申请材料中的源代码素材，展示系统分层、模块职责、接口命名和异常处理方式。
"""

    def _contract_test_py(self, analysis: AnalysisResult) -> str:
        expected = [module.slug for module in analysis.core_modules]
        return f'''"""Contract tests for generated source layout."""

EXPECTED_MODULES = {expected!r}


def test_expected_modules_are_declared():
    assert EXPECTED_MODULES
    assert all(module.startswith("module_") for module in EXPECTED_MODULES)
'''

    def _pad_with_methods(self, lines: list[str], target_lines: int, prefix: str) -> str:
        method_prefix = self._snake_name(prefix)
        index = 1
        while len(lines) < target_lines:
            lines.extend(
                [
                    f"    def {method_prefix}_{index:02d}(self, payload: dict | None = None) -> dict:",
                    f'        """Apply generated business rule {index:02d}."""',
                    "        payload = dict(payload or {})",
                    f"        payload.setdefault(\"rule\", \"{prefix}_{index:02d}\")",
                    "        payload.setdefault(\"handled\", True)",
                    "        return payload",
                    "",
                ]
            )
            index += 1
        return "\n".join(lines)

    def _class_name(self, slug: str, suffix: str) -> str:
        parts = [part for part in slug.split("_") if not part.isdigit() and part != "module"]
        return "".join(part.capitalize() for part in parts) + suffix

    def _snake_name(self, value: str) -> str:
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
        name = re.sub(r"[^a-z0-9_]+", "_", name).strip("_")
        return name or "generated_rule"
