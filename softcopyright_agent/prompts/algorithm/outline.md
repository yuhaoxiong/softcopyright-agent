你是一位 AI/算法行业架构师。请根据标题分析生成适用于算法类软著的设计说明书目录和源代码目录规划。

标题分析：{analysis}
目标总字数：{target_words}

## 算法软著七章结构

| 章节 | 标题 | 算法侧重点 | 必须图表 |
|---|---|---|---|
| 第1章 | 软件概述 | 算法背景、研究问题、数据来源 | 无 |
| 第2章 | 系统架构图 | 训练-推理管线架构、GPU部署拓扑 | `graph TD` × 2-3 |
| 第3章 | 功能模块设计 | 数据处理/训练/推理/评估/版本管理 | `graph TD` × 1 |
| 第4章 | 核心算法与流程 | 模型架构、损失函数、训练策略、推理流程 | `flowchart TD` × 3+ |
| 第5章 | 数据结构设计 | Dataset、Feature、ModelArtifact、Metric | `classDiagram` × 1 |
| 第6章 | 接口设计 | 推理API、模型管理API、数据导入接口 | `sequenceDiagram` × 1 |
| 第7章 | 异常处理设计 | GPU OOM、数据质量异常、模型退化检测 | `flowchart TD` × 1 |

### 子节指引

**第 1 章**：1.1 研究背景与问题定义、1.2 算法目标与性能指标、1.3 数据来源与标注规范、1.4 运行环境与GPU配置、1.5 核心算法创新点、1.6 与同类方案对比优势

**第 4 章（本主题重点，字数应占总字数 25%+）**：
- 4.1 算法总体流程（含完整训练-推理管线流程图）
- 4.2 模型网络架构设计（含架构示意图）
- 4.3 损失函数与优化策略
- 4.4 推理与后处理流程
- 4.5 性能评估与基准对比

## 输出格式

只输出 JSON：

{{
  "chapters": [
    {{"id": "chapter_1", "title": "1. 软件概述", "target_words": 1500, "sections": ["1.1 研究背景与问题定义"]}}
  ],
  "code_structure": {{
    "root": ["main.py", "README.md", "requirements.txt"],
    "data": ["module_01_dataset.py", "module_02_preprocess.py"],
    "models": ["module_03_network.py", "module_04_loss.py"],
    "training": ["module_05_trainer.py"],
    "inference": ["module_06_predictor.py"],
    "evaluation": ["module_07_metrics.py"],
    "tests": ["test_module_03_network.py"]
  }}
}}
