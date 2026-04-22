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
    "frontend": "前端框架，如 Vue.js + Element Plus",
    "backend": "后端框架，如 Python + Flask",
    "database": "数据库，如 MySQL + Redis",
    "ai_framework": "AI框架（如涉及），如 PyTorch + Transformers，不涉及则填 无",
    "deployment": "部署方案，如 Docker + Nginx"
  }},
  "business_domain": "业务领域，一句话描述，如 智能客服/知识问答",
  "architecture_style": "架构风格，如 分层架构 + REST API + 模块化服务",
  "deployment_profile": "部署概况，一句话描述",
  "core_modules": [
    {{
      "name": "模块中文名称，如 用户管理模块",
      "slug": "模块英文标识，如 module_01_user，格式为 module_序号_英文缩写",
      "responsibilities": ["职责1", "职责2", "职责3"],
      "entities": ["实体1", "实体2", "实体3"],
      "interfaces": ["create_module_01_user", "update_module_01_user", "query_module_01_user"]
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

1. 基于上述“输入参数向导参考”进行针对性架构延展。如果偏好为“默认”，则由大模型依据标题自行推断最合适的技术栈。
2. `tech_stack` 字段必须包含用户指定的偏好元素。
3. 如果 `has_mobile` 为 True，`core_modules` 必须加入移动应用相关的端侧模块。
4. 如果 `has_algo` 为 True，必须规划硬核算法相关模块。
5. `core_modules` 必须包含 5-8 个模块。每个模块的 `slug` 格式为 `module_序号(两位)_英文缩写`。
6. 技术选型和架构绝不可臆测，必须与生成的模块设计完美对齐。
7. 只输出严谨的 JSON，绝对不要掺杂任何 Markdown 代码块外的文字解释！
