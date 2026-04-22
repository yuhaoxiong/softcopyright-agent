# 软著编写 Agent

软著编写 Agent 是一个本地 Python 工具，用于根据软件著作权标题生成登记材料草稿。它可以自动完成标题分析、说明书目录规划、说明书正文撰写、示例源代码生成、文本风格整理、DOCX/Markdown/报告输出，并提供 Streamlit 可视化界面和人工审查流程。

> 说明：本项目用于辅助生成和整理软著材料草稿。生成内容仍需人工审校，不应被视为法律意见或最终申报材料。

## 功能特性

- 标题分析：根据软著标题推断业务领域、技术栈、核心模块和部署方式。
- 说明书生成：按章节目标字数生成 Markdown 说明书，并可导出 DOCX。
- 源代码素材生成：按模块生成可读的 Python 示例工程结构和测试契约。
- 大模型增强：支持 OpenAI-compatible Chat Completions 接口，也支持 xAI/Grok 配置。
- 离线 fallback：未配置 API Key 时使用本地确定性生成逻辑，便于测试和演示。
- 人工审查：可将目录、说明书章节、源码草稿写入审查目录，支持人工修改后继续。
- Streamlit UI：提供标题配置、生成进度、文件浏览、在线编辑和打包下载能力。

## 项目结构

```text
softcopyright_agent/
  agent.py                 # 六阶段编排入口
  cli.py                   # 命令行入口
  analyzer.py              # 标题分析
  outline_generator.py     # 说明书目录生成
  doc_writer.py            # 说明书正文生成
  code_generator.py        # 源代码素材生成
  output_formatter.py      # Markdown/DOCX/报告/元数据输出
  review.py                # 人工审查草稿管理
  ui.py                    # Streamlit 界面
  utils/                   # 文件、安全路径、字数、行数、DOCX、图表工具
tests/                     # 单元测试
docs/                      # 需求、方案和分析文档
pyproject.toml             # Python 包配置
```

## 环境要求

- Python 3.10 或更高版本
- Windows、macOS、Linux 均可运行
- 可选：OpenAI-compatible API Key，用于大模型增强生成

## 安装

建议在虚拟环境中安装：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
```

如果只想运行测试，也可以直接在项目根目录执行：

```powershell
python -m unittest discover -s tests
```

## 命令行使用

默认模式会优先尝试大模型；如果未配置 API Key，会自动回退到本地生成：

```powershell
python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/demo
```

低阈值快速验证：

```powershell
python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/sample --doc-words 1200 --code-lines 350 --no-docx
```

常用参数：

```text
--output              输出目录，默认 outputs/generated
--doc-words           说明书目标字数，默认 9000
--code-lines          源代码目标行数，默认 3000
--no-docx             跳过 DOCX 输出
--llm-provider        auto | openai-compatible | grok | fallback
--llm-required        强制使用大模型，失败时不回退
--interactive-review  启用交互式人工审查
--review-dir          指定人工审查草稿目录
```

## 大模型配置

OpenAI-compatible 示例：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:SOFTCOPYRIGHT_LLM_MODEL="你的模型名"
python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/demo --llm-provider openai-compatible
```

Grok 示例：

```powershell
$env:XAI_API_KEY="你的 xAI API Key"
python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/demo --llm-provider grok
```

可用环境变量：

- `OPENAI_API_KEY` 或 `SOFTCOPYRIGHT_LLM_API_KEY`
- `OPENAI_BASE_URL` 或 `SOFTCOPYRIGHT_LLM_BASE_URL`
- `OPENAI_MODEL` 或 `SOFTCOPYRIGHT_LLM_MODEL`
- `XAI_API_KEY`
- `XAI_BASE_URL`
- `XAI_MODEL`

`OPENAI_BASE_URL` 可以配置为 `https://api.openai.com/v1`，程序会自动补齐 `/chat/completions`。

## 人工审查流程

只写入审查草稿、不暂停：

```powershell
python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/demo --review-dir outputs/demo-review
```

启用交互式暂停，允许人工修改后继续：

```powershell
python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/demo --interactive-review
```

审查目录包含：

- `01_outline.json`
- `02_document/*.md`
- `03_code/**`

## Streamlit UI

启动界面：

```powershell
python -m streamlit run softcopyright_agent/ui.py
```

界面支持标题配置、目标字数/行数、API 配置、生成进度、输出文件浏览、文本在线编辑、审查草稿继续生成和 ZIP 打包下载。

## 输出文件

一次生成通常会产出：

- `{标题}_设计说明书.md`
- `{标题}_设计说明书.docx`
- `{标题}_源代码/`
- `{标题}_生成报告.md`
- `{标题}_metadata.json`

## 测试状态

当前测试命令：

```powershell
python -m unittest discover -s tests
```

测试覆盖核心生成链路、CLI 输出、LLM 配置、人工审查、安全路径校验、DOCX/Markdown 输出和 UI 文件辅助函数。

## 发布注意事项

- `outputs/`、`venv/`、`__pycache__/`、`*.egg-info/` 等本地生成物不应提交到仓库。
- Mermaid 远程渲染默认关闭；如需调用 Kroki，可设置 `SOFTCOPYRIGHT_ENABLE_REMOTE_DIAGRAMS=1`。
- `aigc_reducer` 只做文本风格整理和人工审校辅助，不承诺绕过任何外部检测系统。
