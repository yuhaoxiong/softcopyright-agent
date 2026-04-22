你是一位软件架构师。请根据标题分析结果生成符合 CPCC 规范的软件著作权设计说明书目录和源代码目录规划。

标题分析：{analysis}
目标总字数：{target_words}

## 目录结构规范

严格使用以下**七章经典结构 + 附录**，不得自行发明根章节。每章必须包含指定数量的子节和图表：

| 章节 | 标题 | 最低子节数 | 必须包含的 Mermaid 图表 |
|---|---|---|---|
| 第1章 | 软件概述 | 6 | 无（纯文字 + 环境配置表格） |
| 第2章 | 系统架构图 | 3 | `graph TD` 逻辑架构图 + 部署架构图 + 数据流图 |
| 第3章 | 功能模块设计 | core_modules 数量 + 1 | `graph TD` 功能结构总览图 |
| 第4章 | 核心算法与流程 | 3 | `flowchart TD` 核心流程图 × 2+ |
| 第5章 | 数据结构设计 | 3 | `classDiagram` 核心类图 + 数据表字段表格 |
| 第6章 | 接口设计 | 3 | `sequenceDiagram` 时序图 + 接口字段表格 |
| 第7章 | 异常处理设计 | 3 | `flowchart TD` 异常检测流程图 |
| 附录 | 术语表与运行指标 | 2 | 术语表格 + 指标表格 |

### 子节详细指引

**第 1 章·软件概述** 必须包含：
- 1.1 背景与建设初衷（行业痛点与解决方案）
- 1.2 建设目标（3-5 个量化目标）
- 1.3 应用场景与业务流程概览（典型业务 bullet list）
- 1.4 运行环境与软硬件条件（Markdown 表格：层级|组件|配置|说明）
- 1.5 关键技术特性（3-5 项技术亮点描述）
- 1.6 创新点与优势

**第 3 章·功能模块设计** 必须：
- 3.1 总述模块划分原则
- 3.2 功能结构图（graph TD 展示模块调用关系）
- 3.3～3.N 每个 core_module 独立子节，含职责描述和 ≥4 条功能要点 bullet list

**第 5 章·数据结构设计** 必须包含：
- classDiagram 核心类图（展示实体关系）
- Markdown 表格列出关键数据表字段（表名|字段|类型|描述）

**第 6 章·接口设计** 必须包含：
- sequenceDiagram 时序图（展示核心模块间调用时序）
- Markdown 表格列出接口字段定义

## 代码目录与文档对齐

`code_structure` 必须满足：
1. 源码文件名包含对应的 `core_modules` 的 `slug`
2. 包含 models/、services/、api/、tests/ 等标准目录
3. 包含 README.md 和 requirements.txt

## 输出格式

只输出严格合法的 JSON，不要有任何额外解释文字或 Markdown 代码块符号：

{{
  "chapters": [
    {{
      "id": "chapter_1",
      "title": "1. 软件概述",
      "target_words": 2000,
      "sections": ["1.1 背景与建设初衷", "1.2 建设目标", "1.3 应用场景与业务流程概览", "1.4 运行环境与软硬件条件", "1.5 关键技术特性", "1.6 创新点与优势"]
    }},
    {{
      "id": "chapter_2",
      "title": "2. 系统架构图",
      "target_words": 1200,
      "sections": ["2.1 架构概述", "2.2 逻辑架构图", "2.3 部署架构图", "2.4 数据流与控制流"]
    }}
  ],
  "code_structure": {{
    "root": ["app.py", "README.md", "requirements.txt"],
    "config": ["settings.py", "constants.py"],
    "models": ["module_01_xxx.py"],
    "services": ["module_01_xxx_service.py"],
    "api": ["module_01_xxx_api.py"],
    "tests": ["test_module_01_xxx.py"]
  }}
}}
