"""Phase 2: outline and code structure generation."""

from __future__ import annotations

import json

from .llm import LLMClient, extract_json_object
from .models import AnalysisResult, Chapter, Outline
from .prompt_engine import PromptEngine


class OutlineGenerator:
    """Build the soft copyright document outline from analysis metadata."""

    def generate(
        self,
        analysis: AnalysisResult,
        target_total_words: int = 9000,
        *,
        llm_client: LLMClient | None = None,
        prompt_engine: PromptEngine | None = None,
    ) -> Outline:
        if llm_client is not None:
            prompt_engine = prompt_engine or PromptEngine()
            prompt = prompt_engine.render(
                "outline.md",
                analysis=json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
                target_words=target_total_words,
            )
            response = llm_client.generate(
                system="你是严谨的软件著作权材料架构师，输出必须是可解析 JSON。",
                user=prompt,
                temperature=0.2,
            )
            return Outline.from_dict(extract_json_object(response))
        return self._fallback_generate(analysis, target_total_words)

    def _fallback_generate(self, analysis: AnalysisResult, target_total_words: int = 9000) -> Outline:
        budgets = self._chapter_budgets(target_total_words)
        module_sections = []
        for index, module in enumerate(analysis.core_modules, start=1):
            module_sections.extend(
                [
                    f"3.{index} {module.name}",
                    f"3.{index}.1 模块概述",
                    f"3.{index}.2 功能设计",
                    f"3.{index}.3 接口设计",
                    f"3.{index}.4 数据结构设计",
                ]
            )

        chapters = [
            Chapter("chapter_1", "1. 引言", budgets[0], ["1.1 编写目的", "1.2 项目背景", "1.3 定义与缩写", "1.4 参考资料"]),
            Chapter("chapter_2", "2. 软件总体设计", budgets[1], ["2.1 设计目标与原则", "2.2 系统架构设计", "2.3 技术选型说明", "2.4 系统运行环境"]),
            Chapter("chapter_3", "3. 模块详细设计", budgets[2], module_sections),
            Chapter("chapter_4", "4. 数据库设计", budgets[3], ["4.1 数据库E-R图说明", "4.2 数据表设计"]),
            Chapter("chapter_5", "5. 系统接口设计", budgets[4], ["5.1 外部接口", "5.2 内部接口"]),
            Chapter("chapter_6", "6. 系统安全设计", budgets[5], ["6.1 身份认证与授权", "6.2 数据安全", "6.3 日志与审计"]),
            Chapter("chapter_7", "7. 系统部署与运维", budgets[6], ["7.1 部署架构", "7.2 运维监控"]),
        ]
        return Outline(chapters=chapters, code_structure=self._code_structure(analysis))

    def _chapter_budgets(self, target_total_words: int) -> list[int]:
        ratios = [0.08, 0.18, 0.45, 0.10, 0.08, 0.06, 0.05]
        minimum = 40 if target_total_words < 2000 else 120
        budgets = [max(minimum, int(target_total_words * ratio)) for ratio in ratios]
        budgets[-1] += target_total_words - sum(budgets)
        if budgets[-1] < minimum:
            shortage = minimum - budgets[-1]
            budgets[-1] = minimum
            for index in sorted(range(len(budgets) - 1), key=lambda item: budgets[item], reverse=True):
                available = budgets[index] - minimum
                if available <= 0:
                    continue
                take = min(available, shortage)
                budgets[index] -= take
                shortage -= take
                if shortage == 0:
                    break
        return budgets

    def _code_structure(self, analysis: AnalysisResult) -> dict[str, list[str]]:
        module_files = [module.slug for module in analysis.core_modules]
        return {
            "root": ["app.py", "README.md"],
            "config": ["__init__.py", "settings.py", "database.py"],
            "models": ["__init__.py", "base.py", *[f"{slug}.py" for slug in module_files]],
            "services": ["__init__.py", *[f"{slug}_service.py" for slug in module_files]],
            "api": ["__init__.py", *[f"{slug}_api.py" for slug in module_files]],
            "utils": ["__init__.py", "auth.py", "logger.py", "validators.py"],
            "tests": ["__init__.py", "test_generated_contract.py"],
        }
