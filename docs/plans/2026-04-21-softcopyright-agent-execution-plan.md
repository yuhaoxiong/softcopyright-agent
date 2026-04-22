# 软著编写 Agent 执行计划

## 内部等级
L。当前仓库为空项目，任务可由单一 governed lane 串行完成；用户未要求子代理或并行委派，因此不启用子代理。

## 阶段
1. 骨架与治理工件：创建需求、计划、运行回执目录。
2. 项目骨架：创建 Python 包、CLI、prompt 模板、测试目录。
3. 核心实现：实现 analyzer、outline、doc writer、code generator、style reducer、output formatter、agent orchestration。
4. 验证：编写单元测试并运行 `python -m unittest discover -s tests`。
5. 清理：写入 phase receipt、cleanup receipt，确认无临时构建残留。

## 所有权边界
- `softcopyright_agent/`：运行时代码。
- `softcopyright_agent/prompts/`：可替换 prompt 模板。
- `softcopyright_agent/templates/`：结构模板。
- `tests/`：标准库 unittest 测试。
- `docs/` 和 `outputs/runtime/`：vibe 运行工件。

## 验证命令
- `python -m unittest discover -s tests`
- `python -m softcopyright_agent "基于深度学习的智能问答系统 V1.0" --output outputs/sample --doc-words 1200 --code-lines 350 --no-docx`

## 回滚规则
- 如测试连续失败三次，停止并报告失败原因。
- 不删除用户原始设计方案。
- 不执行破坏性 Git 或文件系统操作。

## 完成语言规则
只有在验证命令通过后，才可声明实现完成。若无法运行某项验证，必须明确说明未验证项和原因。

## 清理期望
- 保留必要的 runtime receipt 和 sample 输出。
- 不保留临时缓存目录。
- 不创建未解释的大型二进制依赖。
