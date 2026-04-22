你是一位资深软件架构师，擅长分析软件著作权标题并推断出合理的技术方案。

## 任务

请分析以下软著标题，输出结构化 JSON。

**标题：** {title}

## 输出要求

严格按以下 JSON 格式输出，不要输出任何其他文字：

```json
{{
  "keywords": ["从标题中提取的技术关键词，3-6个"],
  "tech_stack": {{
    "frontend": "前端框架（含版本号），如 Vue 3.4 + Element Plus 2.7；若为纯后端/嵌入式则填 无",
    "backend": "后端框架（含版本号），如 Python 3.11 + Flask 3.0；若为纯前端则填 无",
    "database": "数据库（含版本号），如 MySQL 8.0 + Redis 7.2",
    "ai_framework": "AI/算法框架（如涉及），如 PyTorch 2.1 + Transformers 4.36，不涉及则填 无",
    "deployment": "部署方案，如 Docker 24.0 + Nginx 1.25 + Gunicorn"
  }},
  "business_domain": "业务领域一句话描述，如 废旧纺织品智能识别与自动分拣",
  "architecture_style": "架构风格，如 感知-推理-决策-执行 四层工业架构",
  "deployment_profile": "部署环境概况，如 工控机+PLC控制柜+HMI触控屏 工业现场部署",
  "core_modules": [
    {{
      "name": "模块中文名称（8字以内），如 高光谱采集模块",
      "slug": "module_序号(两位)_英文缩写，如 module_01_spectral",
      "responsibilities": ["职责1（动词+宾语格式）", "职责2", "职责3", "职责4"],
      "entities": ["核心数据实体1", "核心数据实体2", "核心数据实体3"],
      "interfaces": ["模块对外接口函数名1", "接口函数名2", "接口函数名3"]
    }}
  ]
}}
```

## 输入参数向导参考

- **应用类型：** {project_type}
- **技术栈偏好：** {tech_stack}
- **数据库偏好：** {database}
- **是否强制包含移动端：** {has_mobile}
- **是否强制包含算法模块：** {has_algo}

## 规则

1. 基于上述"输入参数向导参考"进行针对性架构延展。偏好为"默认"时，依据标题推断最合适的技术栈。
2. `tech_stack` 各字段必须携带**具体版本号**（如 Python 3.11、MySQL 8.0），不得模糊写"Python"。
3. 如果 `has_mobile` 为 True，`core_modules` 必须加入移动端相关模块。
4. 如果 `has_algo` 为 True，必须规划包含模型训练/推理的硬核算法模块。
5. `core_modules` 必须包含 5-8 个模块。每模块 `responsibilities` 不少于 4 项，`entities` 不少于 3 项。
6. 推断时必须考虑标题暗示的**行业场景**（如工业检测→PLC通信协议、医疗→HL7/DICOM接口、教育→课程/考试实体），确保模块规划反映行业纵深而非通用模板。
7. 技术选型和架构绝不可臆测，必须与生成的模块设计完美对齐。
8. 只输出严谨的 JSON，绝对不要掺杂任何 Markdown 代码块外的文字解释！
