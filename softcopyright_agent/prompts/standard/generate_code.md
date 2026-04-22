请根据软著说明书模块规划生成源代码素材。

标题分析：{analysis}
目录规划：{outline}
说明书上下文：{document_context}
当前模块：{module}
目标行数：{target_lines}

## 代码质量要求

1. **模块对齐**：代码文件必须与说明书中的模块一一对应，文件名包含模块 slug。
2. **文档性**：
   - 每个文件顶部必须有模块级 docstring，说明模块职责和主要类/函数
   - 每个类和公开方法必须有 docstring
   - 关键业务逻辑处必须有行内注释
3. **类型注解**：所有函数参数和返回值必须有 Python 类型注解（`def func(param: str) -> dict:`）
4. **错误处理**：
   - 每个 service 类至少包含 2 个 try-except 块
   - 定义模块级自定义异常类（如 `class UserServiceError(Exception): ...`）
5. **模块间引用**：在 import 区域体现模块间调用关系（如 `from models.module_01_user import UserModel`）
6. **禁止凑行数**：不得重复定义相似函数。通过增加业务方法、配置常量、数据验证逻辑来达到目标行数。
7. **用途声明**：代码用于软著申请材料展示，不要求连接真实外部服务，但逻辑结构必须完整可读。

## 输出格式

只输出严格合法的 JSON 数组，不要输出任何解释文字：

[
  {{"path": "services/example_service.py", "content": "文件完整内容"}}
]
