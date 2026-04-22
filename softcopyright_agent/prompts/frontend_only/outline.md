你是一位前端架构师。请根据标题分析生成适用于纯前端软著的设计说明书目录和源代码目录规划。

标题分析：{analysis}
目标总字数：{target_words}

## 纯前端软著七章结构

| 章节 | 标题 | 前端侧重点 | 必须图表 |
|---|---|---|---|
| 第1章 | 软件概述 | 应用场景、浏览器兼容、技术选型 | 无 |
| 第2章 | 系统架构图 | 前端分层架构、组件树架构、构建部署流程 | `graph TD` × 2-3 |
| 第3章 | 功能模块设计 | 路由/状态/组件/请求/权限 等前端模块 | `graph TD` × 1 |
| 第4章 | 核心算法与流程 | 渲染优化、状态流转、表单校验逻辑 | `flowchart TD` × 2+ |
| 第5章 | 数据结构设计 | Store State、API Response DTO、组件Props | `classDiagram` × 1 |
| 第6章 | 接口设计 | RESTful API消费、WebSocket、组件通信 | `sequenceDiagram` × 1 |
| 第7章 | 异常处理设计 | 网络异常、Token过期、渲染错误边界 | `flowchart TD` × 1 |

### 子节指引

**第 1 章**：1.1 应用背景与目标用户、1.2 开发目标与核心功能、1.3 用户交互流程概览、1.4 运行环境与浏览器兼容性、1.5 关键技术特性、1.6 创新点与设计亮点

**第 4 章**：
- 4.1 前端渲染与交互总流程
- 4.2 状态管理流转逻辑（Action→Reducer→State→View）
- 4.3 表单校验/动态配置核心逻辑

**第 5 章**：数据结构聚焦 Store Shape、API Response 类型定义、组件 Props/Emits 接口

## 输出格式

只输出 JSON：

{{
  "chapters": [
    {{"id": "chapter_1", "title": "1. 软件概述", "target_words": 1800, "sections": ["1.1 应用背景与目标用户"]}}
  ],
  "code_structure": {{
    "root": ["index.html", "README.md", "package.json"],
    "src/components": ["module_01_layout.tsx"],
    "src/store": ["module_02_state.ts"],
    "src/router": ["module_03_router.ts"],
    "src/services": ["module_04_api.ts"],
    "src/hooks": ["module_05_auth.ts"],
    "tests": ["test_module_01_layout.test.ts"]
  }}
}}
