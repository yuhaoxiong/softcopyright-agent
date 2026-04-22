请根据纯前端软著说明书模块规划生成源代码素材。

标题分析：{analysis}
目录规划：{outline}
说明书上下文：{document_context}
当前模块：{module}
目标行数：{target_lines}

## 前端代码风格

1. 使用 TypeScript + React 风格（或 Vue 3 Composition API，根据 tech_stack 选择）。
2. 体现前端设计模式：
   - 函数式组件 + Hooks 模式
   - 容器组件/展示组件分离
   - 自定义 Hook 封装业务逻辑
   - Store 切片（Slice）模式管理状态
3. 必须包含 TypeScript 类型定义（interface/type）。
4. 必须包含 JSDoc 注释。
5. 错误处理：ErrorBoundary、请求拦截器异常、表单校验异常。
6. 模块间引用体现前端依赖关系（如组件引用 Store Hook，Service 引用 API Client）。

## 输出格式

只输出 JSON 数组：

[
  {{"path": "src/components/module_01_layout.tsx", "content": "文件完整内容"}}
]
