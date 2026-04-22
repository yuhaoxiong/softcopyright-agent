# 软著编写 Agent LLM 化改造执行计划

## 内部等级
L。改造涉及多模块但边界清晰，采用单 lane 串行完成。

## 执行阶段
1. 新增 `llm.py` 和 `prompt_engine.py`：封装 OpenAI-compatible 请求、JSON 提取、prompt 渲染和 fallback。
2. 新增 `review.py`：实现目录、说明书和代码审查检查点。
3. 改造 `OutlineGenerator`、`DocumentWriter`、`CodeGenerator`：支持 LLM 优先，失败时 fallback。
4. 改造 `SoftCopyrightAgent` 和 CLI：注入 LLM、审查配置、报告元数据。
5. 补充 fake LLM 测试，验证无网络环境下的 LLM 路径。
6. 运行 `python -m unittest discover -s tests` 和 CLI 低阈值验证。

## 验证命令
- `python -m unittest discover -s tests`
- `python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/llm-check --doc-words 1200 --code-lines 350 --no-docx --llm-provider fallback`

## 回滚规则
- 不删除原始设计方案。
- 不移除离线 fallback。
- 如 LLM JSON 解析失败，不中断默认流程，记录 fallback；若用户指定 `--llm-required` 则失败退出。
