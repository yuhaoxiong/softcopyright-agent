"""Phase 1: title analysis.

Supports both LLM-powered structured analysis and deterministic fallback.
"""

from __future__ import annotations

import json

from .llm import LLMClient, LLMError, extract_json_object
from .models import AnalysisResult, ModuleSpec
from .prompt_engine import PromptEngine


class TitleAnalyzer:
    """Infer a practical software architecture from a copyright title."""

    def analyze(
        self,
        title: str,
        *,
        llm_client: LLMClient | None = None,
        prompt_engine: PromptEngine | None = None,
        **kwargs: object,
    ) -> AnalysisResult:
        normalized = title.strip()
        if not normalized:
            raise ValueError("软著标题不能为空")

        if llm_client is not None:
            return self._analyze_with_llm(
                normalized,
                llm_client,
                prompt_engine or PromptEngine(),
                **kwargs,
            )

        return self._fallback_analyze(normalized)

    # ── LLM 分析 ────────────────────────────────────────────────
    def _analyze_with_llm(
        self,
        title: str,
        llm_client: LLMClient,
        prompt_engine: PromptEngine,
        **kwargs: object,
    ) -> AnalysisResult:
        """Call LLM to produce a structured analysis from any title."""
        context = {"title": title, **kwargs}
        prompt = prompt_engine.render("analyze.md", **context)
        response = llm_client.generate(
            system="你是严谨的软件著作权材料架构师，输出必须是可解析 JSON。",
            user=prompt,
            temperature=0.2,
        )
        data = extract_json_object(response)
        if not isinstance(data, dict):
            raise ValueError("LLM 标题分析未返回 JSON 对象")
        return self._parse_llm_result(title, data)

    def _parse_llm_result(self, title: str, data: dict) -> AnalysisResult:
        """Convert LLM JSON output to AnalysisResult, with defensive defaults."""
        keywords = list(data.get("keywords", ["业务管理", "数据处理"]))
        tech_stack = data.get("tech_stack", {})
        if not isinstance(tech_stack, dict):
            tech_stack = {}
        tech_stack.setdefault("frontend", "Vue.js + Element Plus")
        tech_stack.setdefault("backend", "Python + Flask")
        tech_stack.setdefault("database", "MySQL + Redis")
        tech_stack.setdefault("ai_framework", "无")
        tech_stack.setdefault("deployment", "Docker + Nginx")

        raw_modules = data.get("core_modules", [])
        modules: list[ModuleSpec] = []
        for item in raw_modules:
            if not isinstance(item, dict):
                continue
            modules.append(
                ModuleSpec(
                    name=str(item.get("name", "未命名模块")),
                    slug=str(item.get("slug", f"module_{len(modules)+1:02d}_unknown")),
                    responsibilities=list(item.get("responsibilities", ["数据处理"])),
                    entities=list(item.get("entities", ["记录"])),
                    interfaces=list(item.get("interfaces", [])),
                )
            )
        if not modules:
            # LLM 没返回有效模块，回退到硬编码
            fallback = self._fallback_analyze(title)
            modules = fallback.core_modules

        return AnalysisResult(
            title=title,
            normalized_title=title.replace(" ", ""),
            keywords=keywords,
            tech_stack=tech_stack,
            business_domain=str(data.get("business_domain", "通用业务信息管理")),
            core_modules=modules[:8],
            architecture_style=str(data.get("architecture_style", "分层架构 + REST API + 模块化服务")),
            deployment_profile=str(data.get("deployment_profile", "单机部署起步，支持 Docker Compose 扩展")),
        )

    # ── 确定性 Fallback ──────────────────────────────────────────
    def _fallback_analyze(self, title: str) -> AnalysisResult:
        """Deterministic analysis using keyword matching (no network)."""
        normalized = title.strip()
        keywords = self._extract_keywords(normalized)
        tech_stack = self._infer_tech_stack(normalized, keywords)
        domain = self._infer_domain(normalized, keywords)
        modules = self._build_modules(normalized, keywords)

        return AnalysisResult(
            title=normalized,
            normalized_title=normalized.replace(" ", ""),
            keywords=keywords,
            tech_stack=tech_stack,
            business_domain=domain,
            core_modules=modules,
            architecture_style="分层架构 + REST API + 模块化服务",
            deployment_profile="单机部署起步，支持 Docker Compose 扩展到应用服务、数据库和检索服务分离部署",
        )

    def _extract_keywords(self, title: str) -> list[str]:
        keyword_candidates = [
            "深度学习",
            "机器学习",
            "智能问答",
            "知识库",
            "数据分析",
            "管理系统",
            "移动端",
            "小程序",
            "物联网",
            "图像识别",
            "自然语言处理",
            "推荐",
            "客服",
            "监控",
            "审批",
            "调度",
            "区块链",
            "供应链",
            "电商",
            "社交",
            "教育",
            "医疗",
            "金融",
            "停车",
            "安防",
            "运维",
        ]
        matches = [word for word in keyword_candidates if word in title]
        if "AI" in title.upper() and "人工智能" not in matches:
            matches.append("人工智能")
        if not matches:
            matches.extend(["业务管理", "数据处理", "系统配置"])
        return matches

    def _infer_tech_stack(self, title: str, keywords: list[str]) -> dict[str, str]:
        stack = {
            "frontend": "Vue.js + Element Plus",
            "backend": "Python + Flask",
            "database": "MySQL + Redis",
            "ai_framework": "可选 PyTorch + Transformers",
            "deployment": "Docker + Nginx",
        }
        joined = title + " ".join(keywords)
        if any(word in joined for word in ["智能问答", "知识库", "自然语言处理", "深度学习", "人工智能"]):
            stack["database"] = "MySQL + Elasticsearch + Redis"
            stack["ai_framework"] = "PyTorch + Transformers"
        if any(word in joined for word in ["移动端", "小程序"]):
            stack["frontend"] = "UniApp + Vue.js"
        if any(word in joined for word in ["图像识别", "视觉", "安防"]):
            stack["ai_framework"] = "PyTorch + OpenCV"
        if any(word in joined for word in ["区块链"]):
            stack["backend"] = "Go + Hyperledger Fabric"
        if any(word in joined for word in ["电商", "金融"]):
            stack["database"] = "MySQL + Redis + MongoDB"
        return stack

    def _infer_domain(self, title: str, keywords: list[str]) -> str:
        joined = title + " ".join(keywords)
        if any(word in joined for word in ["智能问答", "客服", "知识库"]):
            return "智能客服/知识问答"
        if any(word in joined for word in ["图像识别", "视觉", "安防"]):
            return "计算机视觉/图像处理"
        if any(word in joined for word in ["物联网", "监控"]):
            return "物联网设备监控"
        if any(word in joined for word in ["审批", "调度", "管理系统", "运维"]):
            return "企业信息化管理"
        if any(word in joined for word in ["电商", "供应链"]):
            return "电子商务/供应链管理"
        if any(word in joined for word in ["教育"]):
            return "在线教育/培训管理"
        if any(word in joined for word in ["医疗"]):
            return "智慧医疗/健康管理"
        if any(word in joined for word in ["金融", "区块链"]):
            return "金融科技/数字资产"
        if any(word in joined for word in ["停车"]):
            return "智慧停车/交通管理"
        return "通用业务信息管理"

    def _build_modules(self, title: str, keywords: list[str]) -> list[ModuleSpec]:
        joined = title + " ".join(keywords)
        modules: list[ModuleSpec] = [
            self._module("用户管理模块", "module_01_user", ["账号注册登录", "角色权限控制", "用户资料维护"]),
        ]

        if any(word in joined for word in ["智能问答", "客服", "自然语言处理"]):
            modules.extend(
                [
                    self._module("智能问答引擎模块", "module_02_qa_engine", ["问题理解", "候选答案召回", "答案排序与反馈"]),
                    self._module("知识库管理模块", "module_03_knowledge", ["文档入库", "知识切片", "索引维护"]),
                    self._module("语义检索模块", "module_04_semantic_search", ["向量检索", "关键词检索", "混合排序"]),
                ]
            )
        elif any(word in joined for word in ["图像识别", "视觉", "安防"]):
            modules.extend(
                [
                    self._module("图像采集模块", "module_02_image_capture", ["图片上传", "格式校验", "预处理"]),
                    self._module("识别推理模块", "module_03_inference", ["模型加载", "批量推理", "置信度评估"]),
                    self._module("结果标注模块", "module_04_annotation", ["识别结果展示", "人工修正", "标注归档"]),
                ]
            )
        else:
            modules.extend(
                [
                    self._module("业务流程管理模块", "module_02_workflow", ["流程配置", "状态流转", "任务分派"]),
                    self._module("数据维护模块", "module_03_data", ["基础资料维护", "批量导入", "数据校验"]),
                    self._module("查询统计模块", "module_04_query", ["多条件查询", "统计汇总", "报表导出"]),
                ]
            )

        if any(word in joined for word in ["深度学习", "机器学习", "人工智能", "推荐"]):
            modules.append(self._module("模型训练与评估模块", "module_05_model_ops", ["样本管理", "训练任务", "模型评估"]))

        modules.extend(
            [
                self._module("数据统计与分析模块", "module_06_statistics", ["指标采集", "趋势分析", "运营看板"]),
                self._module("系统配置管理模块", "module_07_settings", ["参数配置", "字典管理", "运行状态检查"]),
                self._module("日志审计模块", "module_08_audit", ["操作日志", "异常追踪", "审计报表"]),
            ]
        )
        return modules[:8]

    def _module(self, name: str, slug: str, responsibilities: list[str]) -> ModuleSpec:
        base = name.removesuffix("模块")
        return ModuleSpec(
            name=name,
            slug=slug,
            responsibilities=responsibilities,
            entities=[f"{base}记录", f"{base}配置", f"{base}日志"],
            interfaces=[f"create_{slug}", f"update_{slug}", f"query_{slug}", f"audit_{slug}"],
        )
