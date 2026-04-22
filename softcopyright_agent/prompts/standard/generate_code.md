请根据软著说明书模块规划生成源代码素材。

标题分析：{analysis}
目录规划：{outline}
说明书上下文：{document_context}
当前模块：{module}
目标行数：{target_lines}

要求：
1. 代码模块必须与说明书模块一一对应。
2. 使用清晰的类名、函数名、docstring、异常处理和注释。
3. 禁止为了凑行数重复定义相似函数。
4. 代码用于软著申请材料展示，不要求连接真实服务。
5. 只输出 JSON，不要输出解释文字。

JSON 结构：
[
  {{"path": "services/example_service.py", "content": "文件完整内容"}}
]
