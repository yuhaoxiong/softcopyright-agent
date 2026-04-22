你是一位资深前端架构师，擅长分析纯前端类软件著作权标题并推断出合理的技术方案。

## 任务

请分析以下纯前端类软著标题，输出结构化 JSON。

**标题：** {title}

## 输出要求

严格按以下 JSON 格式输出：

```json
{{
  "keywords": ["从标题中提取的前端技术关键词，3-6个，如 组件化、响应式布局、状态管理"],
  "tech_stack": {{
    "frontend": "前端框架（含版本号），如 React 18.2 + TypeScript 5.3 + Ant Design 5.12",
    "backend": "无独立后端（API由第三方提供）或 Next.js 14 SSR",
    "database": "客户端存储方案，如 IndexedDB + localStorage / 无",
    "ai_framework": "前端AI能力（如涉及），如 TensorFlow.js 4.15 + ONNX Runtime Web，不涉及填 无",
    "deployment": "部署方案，如 Vercel + CDN / Nginx 静态托管 + Docker"
  }},
  "business_domain": "前端应用类型，如 企业级后台管理系统 / 可视化大屏 / 在线编辑器",
  "architecture_style": "前端架构，如 组件化分层架构(展示层+逻辑层+数据层) + 单向数据流",
  "deployment_profile": "部署环境，如 浏览器端SPA + CDN全球加速",
  "core_modules": [
    {{
      "name": "模块中文名称，如 路由导航模块",
      "slug": "module_序号_英文缩写，如 module_01_router",
      "responsibilities": ["职责1", "职责2", "职责3", "职责4"],
      "entities": ["前端实体/组件1", "实体2", "实体3"],
      "interfaces": ["Hook/组件接口1", "接口2", "接口3"]
    }}
  ]
}}
```

## 输入参数向导参考

- **应用类型：** {project_type}
- **技术栈偏好：** {tech_stack}
- **数据库偏好：** {database}
- **是否强制包含移动端：** {has_mobile}
- **是否强制包含算法模块：** {has_algo}

## 纯前端行业规则

1. `core_modules` 必须包含 5-8 个前端模块。典型模块包括：
   - 路由与导航模块（路由配置、守卫、懒加载、面包屑）
   - 状态管理模块（全局Store、持久化、中间件）
   - 组件库/设计系统模块（原子组件、复合组件、主题Token）
   - 数据请求模块（Axios封装、拦截器、缓存、错误重试）
   - 权限与认证模块（Token管理、角色鉴权、路由守卫）
   - 可视化/图表模块（ECharts/D3封装、数据适配器）
   - 布局与响应式模块（自适应布局、断点系统、暗色模式）
   - 表单与校验模块（动态表单、校验规则引擎、联动逻辑）
2. 技术选型必须匹配前端生态（React→Redux/Zustand，Vue→Pinia，Angular→RxJS/NgRx）。
3. 只输出严谨的 JSON！
