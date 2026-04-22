请根据工控/物联网类软著说明书模块规划生成源代码素材。

标题分析：{analysis}
目录规划：{outline}
说明书上下文：{document_context}
当前模块：{module}
目标行数：{target_lines}

## 工控代码风格

1. 使用 Python 上位机编程风格。类命名采用工控行业惯例（如 `SensorAcquisition`、`PLCCommander`、`SignalProcessor`、`AlarmManager`）。
2. 体现工控软件模式：
   - 传感器采集类（含触发配置、数据缓存、状态监测方法）
   - PLC通信类（Modbus TCP/RTU 读写寄存器、报文组装/解析）
   - 信号处理类（滤波、校准、特征提取管线）
   - 调度器类（任务队列、多设备协调、优先级排序）
   - 监控/报警类（阈值判断、报警记录、通知分发）
3. 必须包含类型注解和详细 docstring。
4. 错误处理：通信超时、传感器断连、设备响应异常、数据校验失败等工控特有异常。
5. 包含通信协议常量定义（如报文头、功能码、寄存器地址映射）。
6. 模块间引用体现工控系统依赖（如调度模块引用PLC通信，监控模块引用传感器采集）。

## 输出格式

只输出 JSON 数组：

[
  {{"path": "control/module_01_plc_comm.py", "content": "文件完整内容"}}
]
