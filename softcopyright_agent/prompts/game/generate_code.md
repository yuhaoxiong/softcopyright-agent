请根据游戏类软著说明书模块规划生成源代码素材。

标题分析：{analysis}
目录规划：{outline}
说明书上下文：{document_context}
当前模块：{module}
目标行数：{target_lines}

## 游戏代码风格

1. 使用 Python 模拟游戏引擎架构。类命名采用游戏行业惯例（如 `GameManager`、`RenderPipeline`、`PhysicsEngine`、`AIController`）。
2. 每个模块顶部 docstring 说明其在游戏引擎中的职责。
3. 必须包含类型注解和 docstring。
4. 体现游戏设计模式：组件模式（Component）、观察者模式（EventBus）、对象池模式（ObjectPool）、状态机模式（StateMachine）。
5. 错误处理：资源加载失败、网络超时、帧率异常等游戏特有异常。
6. 模块间引用体现游戏系统依赖（如渲染模块引用资源管理，AI模块引用寻路模块）。

## 输出格式

只输出 JSON 数组：

[
  {{"path": "engine/module_01_render.py", "content": "文件完整内容"}}
]
