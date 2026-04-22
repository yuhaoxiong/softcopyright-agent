请根据算法类软著说明书模块规划生成源代码素材。

标题分析：{analysis}
目录规划：{outline}
说明书上下文：{document_context}
当前模块：{module}
目标行数：{target_lines}

## 算法代码风格

1. 使用 Python + PyTorch 风格。类命名采用 ML 行业惯例（如 `BaseModel`、`Trainer`、`Dataset`、`Evaluator`）。
2. 体现深度学习代码模式：
   - `nn.Module` 子类定义网络结构
   - `Dataset` / `DataLoader` 数据加载模式
   - `Trainer` 训练循环（含 epoch/batch/loss/optimizer）
   - `Predictor` 推理服务（含模型加载/预处理/后处理）
3. 必须包含类型注解和详细 docstring。
4. 错误处理：GPU内存不足、模型文件损坏、数据格式异常等 ML 特有异常。
5. 包含配置类（超参数、学习率、batch_size 等）。

## 输出格式

只输出 JSON 数组：

[
  {{"path": "models/module_01_network.py", "content": "文件完整内容"}}
]
