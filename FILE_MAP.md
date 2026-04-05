# 文件作用描述 + 冗余分析

> 最后更新：2026-04-03（架构优化：移除降级策略、类型去重、死代码清理、deps.py 脱敏工具统一）

---

## 图例

- ✅ 核心，正常使用
- ⚠️ 存在但有内部冗余
- ❌ 完全未被引用，可删除

---

## 根目录

| 文件 | 状态 | 作用 |
|------|------|------|
| `.env` | ✅ | 实际运行环境变量（LLM Key、JWT Secret），不进版本控制 |
| `.env.example` | ✅ | 环境变量模板，说明所有可配置项及默认值 |
| `.gitignore` | ✅ | Git 忽略规则 |
| `CLAUDE.md` | ✅ | Claude Code 工作指南：目录结构、启动命令、已知问题、调试流程 |
| `README.md` | ✅ | 项目说明：技术栈、快速开始、核心功能、API 列表 |
| `FILE_MAP.md` | ✅ | 本文件：文件作用描述与冗余分析 |
| `requirements.txt` | ✅ | Python 依赖清单 |
| `backend.log / backend_err.log / frontend.log` | ✅ | 运行时日志，每次重启覆盖 |

---

## app/ — 后端

### 顶层

| 文件 | 状态 | 作用 | 冗余说明 |
|------|------|------|----------|
| `main.py` | ✅ | FastAPI 应用入口，含全部路由（Pydantic 模型已提取至 schemas/api.py，认证守卫统一由 deps.py 提供） | — |
| `deps.py` | ✅ | 共享依赖：`get_current_user` / `require_role` / `audit_log` / `_mask_sensitive` / `_mask_student_id` / `_mask_phone` / `_mask_email`（脱敏函数从 main.py 迁入） | — |
| `config.py` | ✅ | pydantic-settings 读取 .env，统一配置管理（已移除 LLM_FALLBACK_PROVIDERS） | — |
| `constants.py` | ✅ | 后端全局常量：DEGREE_MAP / WEIGHT_PRESETS / SKILL_SUGGESTIONS | — |

### app/agents/ — CrewAI 多智能体

| 文件 | 状态 | 作用 |
|------|------|------|
| `crewai_agents.py` | ✅ | 定义各角色 Agent 及工具 |
| `crewai_config.py` | ✅ | Agent 配置参数 |
| `crew_manager.py` | ✅ | 多 Agent 编排入口 |
| `task_manager.py` | ✅ | Agent 任务定义与生命周期管理 |
| `crews/career_crew.py` | ✅ | 职业规划专用工作流 |
| `tools/__init__.py` | ✅ | Agent 工具注册入口（crewai 1.12.2 已安装，CREWAI_TOOLS_AVAILABLE=True）|

### app/ai/ — LLM 集成

| 文件 | 状态 | 作用 | 冗余说明 |
|------|------|------|----------|
| `llm_client.py` | ✅ | 统一 LLM 客户端：单供应商直连（已移除 FallbackLLMClient 降级链） | — |
| `llm_calibrator.py` | ✅ | LLM 输出后处理，被 llm_client 引用 | — |
| `embedding_service.py` | ✅ | 文本向量化，基于本地 all-MiniLM-L6-v2 | — |
| `prompts/student_portrait_v1.jinja2` | ✅ | 简历结构化提取提示词（**实际使用**） | — |
| `prompts/match_analysis_v1.jinja2` | ✅ | 职业素质/发展潜力 LLM 评估（**实际使用**） | — |
| `prompts/report_action_plan_v1.jinja2` | ✅ | 行动计划生成（**实际使用**） | — |
| `prompts/chat_agent_v1.jinja2` | ✅ | AI 对话顾问主提示词（**实际使用**） | — |
| `prompts/emotion_support_v1.jinja2` | ✅ | 情绪支持分支提示词 | — |
| `prompts/polish_report_v1.jinja2` | ✅ | 报告润色提示词 | — |

### app/core/ — 基础设施

| 文件 | 状态 | 作用 | 冗余说明 |
|------|------|------|----------|
| `scheduler.py` | ✅ | APScheduler 定时任务：每日 00:30 抓取 JD、每日 01:00 刷新趋势快照 | — |

### app/data/ — 数据处理辅助

| 文件 | 状态 | 作用 | 冗余说明 |
|------|------|------|----------|
| `job_skills_extended.py` | ✅ | 技能扩展/同义词，被 match_service_optimized 引用 | — |
| `industry_insights.py` | ✅ | 8 个行业深度洞察数据（growth_rate/hot_skills/hiring_seasons/interview_focus/competitive_ratio/top_cities/career_paths）；被 report_service 引用 | — |
| `assessment_questions.py` | ✅ | 三套题库：逻辑推理（5题）、职业倾向（10题 MBTI-like）、技术自评（5岗位×8题）；`get_questions_for_job()` / `calculate_assessment_score()` 工具函数；被 `/api/assessment` 端点引用 | — |

### app/db/ — 数据库

| 文件 | 状态 | 作用 |
|------|------|------|
| `database.py` | ✅ | SQLite 异步连接池，提供 get_db_session |
| `models.py` | ✅ | 全部 ORM 模型 |
| `crud/student_crud.py` | ✅ | 学生数据 CRUD |
| `crud/match_result_crud.py` | ✅ | 匹配结果 CRUD |
| `crud/report_crud.py` | ✅ | 报告 CRUD |
| `crud/chat_session_crud.py` | ✅ | 对话会话 CRUD |
| `crud/portrait_history_crud.py` | ✅ | 画像历史 CRUD |
| `crud/job_real_crud.py` | ✅ | 真实岗位数据 CRUD |
| `crud/job_trend_crud.py` | ✅ | 岗位趋势数据 CRUD |
| `crud/live_job_crud.py` | ✅ | 实时抓取岗位 CRUD（upsert_batch / expire_old）|
| `crud/user_memory_crud.py` | ✅ | 跨会话用户记忆 CRUD（save_user_memory / load_user_memory）|

### app/graph/

| 文件 | 状态 | 作用 |
|------|------|------|
| `job_graph_repo.py` | ✅ | 岗位知识图谱访问：技能扩展、晋升/换岗路径检索 |

### app/routers/

| 文件 | 状态 | 作用 |
|------|------|------|
| `agent.py` | ✅ | CrewAI 多智能体 API 路由（/api/agent/...） |
| `admin.py` | ✅ | 管理员端路由（/api/admin/...） |
| `company.py` | ✅ | 企业端路由（/api/company/...） |
| `assessment.py` | ✅ | 能力测评路由（/api/assessment/...） |

### app/schemas/

| 文件 | 状态 | 作用 |
|------|------|------|
| `api.py` | ✅ | 全部 API 请求/响应 Pydantic 模型（从 main.py 提取，20 个类） |

### app/services/ — 业务逻辑

| 文件 | 状态 | 作用 | 冗余说明 |
|------|------|------|----------|
| `resume_service.py` | ✅ | 简历解析主入口 + `ResumeParseResponse` / `ResumeUploadResponse` 响应模型（从 resume_response.py 合并） | — |
| `resume_enhanced.py` | ✅ | 增强字段提取 & 质量评估，被 resume_service 引用 | — |
| `pdf_parser.py` | ✅ | PDF 文本提取：pdfplumber + PyMuPDF + OCR 兜底 | — |
| `portrait_service.py` | ✅ | 学生画像：六维整合 → 竞争力评分 → 软技能推断 | — |
| `job_graph_enhanced.py` | ✅ | 岗位图谱增强查询，被 portrait_service 引用 | — |
| `match_service.py` | ✅ | 人岗匹配主流程（五维度） | — |
| `match_service_optimized.py` | ✅ | OptimizedSkillMatcher：多层技能匹配（被 match_service 引用）；已删除未使用的 MatchResultCache / MatchErrorHandler | — |
| `chat_agent_service.py` | ✅ | AI 对话：九状态 FSM + ReAct 推理链（6工具）+ 跨会话记忆 + 流式 SSE | — |
| `report_service.py` | ✅ | 职业报告生成：六章结构 + LLM 行动计划；已内联 ReportEnhancer（原 report_enhanced.py） | — |
| `report_export_service.py` | ✅ | 报告导出：Word / HTML / PDF | — |
| `recommend_service_optimized.py` | ✅ | 个性化岗位推荐（/api/match/recommend 懒加载） | — |
| `stats_service.py` | ✅ | 用户统计：技能得分历史、竞争力曲线、成就 | — |
| `market_service.py` | ✅ | 市场数据：行业趋势、学习资源推荐 | — |
| `rag_service.py` | ✅ | RAG 检索增强：JSON 关键词降级检索（不依赖 chromadb），match_service 中懒加载 | — |
| `job_fetcher.py` | ✅ | 实时 JD 抓取：适配器模式（RemotiveAdapter + LocalGeneratorAdapter 兜底），被 scheduler 调用 | — |

---

## data/ — 数据文件

| 文件 | 状态 | 作用 |
|------|------|------|
| `career.db` | ✅ | SQLite 数据库：用户/学生/匹配/报告/对话/真实JD/趋势/live_jobs/用户记忆 |
| `job_graph.json` | ✅ | 岗位知识图谱：335节点（225岗位+146技能）590条边，由 rebuild_data.py 生成 |
| `job_profiles.json` | ✅ | 51个岗位画像（与XLS真实数据对齐，total_jd_count已更新） |
| `knowledge_base.json` | ✅ | 本地知识库：30条岗位知识条目（RAG检索 + 赛题提交材料①）|
| `reports/` | ✅ | 导出报告缓存目录（Word/HTML/PDF 临时文件） |

---

## scripts/

| 文件 | 状态 | 作用 |
|------|------|------|
| `download_models.py` | ✅ | 下载 all-MiniLM-L6-v2 嵌入模型到本地 |
| `rebuild_data.py` | ✅ | 从 XLS 重建 job_profiles.json（清除合成重复）+ job_graph.json |
| `import_xls_to_db.py` | ✅ | 将 9958 条真实 JD 批量导入 SQLite job_real 表 |

---

## frontend/src/

### 配置

| 文件 | 状态 | 作用 |
|------|------|------|
| `index.html` | ✅ | Vue 应用 HTML 入口模板 |
| `package.json` | ✅ | 前端依赖清单 |
| `vite.config.ts` | ✅ | Vite 配置：端口 5173，/api 代理到 8000 |
| `tsconfig.json / tsconfig.node.json` | ✅ | TypeScript 编译配置 |

### src/ 顶层

| 文件 | 状态 | 作用 |
|------|------|------|
| `main.ts` | ✅ | Vue 应用初始化：Pinia / Router / Arco Design |
| `App.vue` | ✅ | 根组件：路由出口 + 全局布局 |
| `constants.ts` | ✅ | 前端全局常量：等级映射、技能标签、消息文案、存储键名等 |
| `vite-env.d.ts` | ✅ | Vite 环境变量类型声明 |
| `shims-vue.d.ts` | ✅ | .vue 文件 TypeScript 模块声明 |
| `shims-vue-router.d.ts` | ✅ | Vue Router 类型增强声明 |

### src/api/

| 文件 | 状态 | 作用 |
|------|------|------|
| `http.ts` | ✅ | axios 实例：JWT 注入、Token 刷新、统一错误处理 |
| `auth.ts` | ✅ | 认证接口：登录 / 注册 / 刷新 / 获取当前用户 |
| `resume.ts` | ✅ | 简历接口：文件上传 / 纯文本解析 |
| `portrait.ts` | ✅ | 画像接口：获取 / 更新 / 历史（已移除死函数 getHistory） |
| `match.ts` | ✅ | 匹配接口：计算 / 岗位列表 / 历史 / 推荐（类型统一从 types/index.ts 导入） |
| `report.ts` | ✅ | 报告接口：生成 / 状态 / 详情 / 润色（已移除死函数 exportWord/exportPdf/exportHtml） |
| `chat.ts` | ✅ | 对话接口：session / 流式 / 历史（已移除死函数 sendMessage/getHistory/updateSessionTitle） |
| `job.ts` | ✅ | 岗位接口：搜索 / 详情 / 职业路径图 / 真实 JD |
| `crew.ts` | ✅ | CrewAI 接口：触发工作流 / 查询状态 |
| `stats.ts` | ✅ | 统计接口：技能得分 / 竞争力历史 / 成就 / 趋势（已移除死函数 getLearningResources） |
| `assessment.ts` | ✅ | 测评接口：`getQuestions(jobHint)` / `submit({student_id, answers, job_hint})` |

### src/views/

| 文件 | 状态 | 路由 | 作用 |
|------|------|------|------|
| `Home.vue` | ✅ | `/home` | 首页：岗位浏览、热门岗位、快速入口 |
| `ResumeUpload.vue` | ✅ | `/upload` | 简历上传：文件拖拽 + 手动录入四步表单 |
| `Portrait.vue` | ✅ | `/portrait` | 学生画像：六维展示、竞争力评分、软技能雷达图 |
| `MatchAnalysis.vue` | ✅ | `/match` | 人岗匹配：五维度评分、技能缺口分析 |
| `ChatAdvisor.vue` | ✅ | `/chat` | AI 对话顾问：流式输出、状态进度、快速操作 |
| `CareerReport.vue` | ✅ | `/report` | 职业报告：六章展示、雷达图、行动计划、导出 |
| `CareerGraph.vue` | ✅ | `/graph/:jobId?` | 岗位知识图谱：ECharts 交互可视化 |
| `JobDetail.vue` | ✅ | `/jobs/:jobId` | 职位详情：JD、技能要求、晋升/换岗路径、行业洞察折叠卡片（含 MarketTrendChart）、地区/文化标签 |
| `Assessment.vue` | ✅ | `/assessment` | 三维度能力测评：逻辑推理 + 职业倾向 + 技术自评，步骤式进度条，结果同步至画像 |
| `Login.vue` | ✅ | `/login` | 登录/注册：三种角色入口 |
| `AdminDashboard.vue` | ✅ | `/admin` | 管理员面板：用户管理、数据统计、日志 |
| `CompanyDashboard.vue` | ✅ | `/company` | 企业面板：岗位发布、反向匹配、收藏管理 |

### src/components/

| 文件 | 状态 | 被引用于 | 作用 |
|------|------|----------|------|
| `NavBar.vue` | ✅ | App.vue | 顶部导航栏 |
| `SkillRadarChart.vue` | ✅ | Portrait | 技能/软技能雷达图 |
| `MarketTrendChart.vue` | ✅ | MatchAnalysis, JobDetail | 行业趋势折线图 |
| `CompetitivenessGauge.vue` | ✅ | Portrait | 竞争力仪表盘 |
| `LearningResourceCard.vue` | ✅ | MatchAnalysis | 技能学习资源卡片 |
| `PersonalizedRecommend.vue` | ✅ | Home | 个性化岗位推荐列表 |
| `ExperienceTimeline.vue` | ✅ | Portrait | 实习/项目经历时间轴 |
| `AgentProcessPanel.vue` | ✅ | MatchAnalysis | CrewAI 工作流执行过程 |
| `AgentStatusPanel.vue` | ✅ | ChatAdvisor | Agent 状态实时显示 |
| `AsyncTaskProgress.vue` | ✅ | JobDetail, MatchAnalysis | 异步任务进度条 |
| `StepProgress.vue` | ✅ | CareerReport, MatchAnalysis, Portrait, ResumeUpload | 步骤进度指示器 |
| `ProgressBar.vue` | ✅ | MatchAnalysis | 通用进度条 |
| `ScoreDisplay.vue` | ✅ | MatchAnalysis | 分数展示（百分比 + 颜色） |
| `FeedbackWidget.vue` | ✅ | CareerReport, MatchAnalysis | 用户反馈组件 |
| `LoginModal.vue` | ✅ | Home, JobDetail, MatchAnalysis | 登录弹窗 |
| `GuestLimitHint.vue` | ✅ | MatchAnalysis | 游客访问限制提示 |
| `UserStatsCard.vue` | ✅ | Home | 用户统计卡片 |
| `EmptyState.vue` | ✅ | MatchAnalysis | 空状态占位 |
| `ErrorBoundary.vue` | ✅ | App.vue | 错误边界（防白屏） |
| `SkeletonLoader.vue` | ✅ | Portrait | 骨架屏加载占位 |
| `graph/CareerTimeline.vue` | ✅ | CareerGraph | 职业路径时间轴 |

### src/stores/

| 文件 | 状态 | 作用 |
|------|------|------|
| `useUserStore.ts` | ✅ | 用户状态：Token、角色、登录/登出、自动刷新 |
| `usePortraitStore.ts` | ✅ | 画像状态：学生 ID、画像数据缓存 |
| `useMatchStore.ts` | ✅ | 匹配状态：当前结果、目标岗位、历史（已移除游客假数据 / migrateGuestData） |
| `useReportStore.ts` | ✅ | 报告状态：ID、生成进度、内容缓存 |
| `useCrewStore.ts` | ✅ | CrewAI 状态：工作流状态、Agent 日志流 |

### src/composables/

| 文件 | 状态 | 作用 |
|------|------|------|
| `useSSE.ts` | ✅ | SSE 封装：连接管理、消息解析、自动重连 |
| `useECharts.ts` | ✅ | ECharts 封装：resize、主题、销毁管理 |
| `useUpload.ts` | ✅ | 文件上传：拖拽、类型/大小校验、进度回调 |

### src/utils/

| 文件 | 状态 | 作用 |
|------|------|------|
| `error.ts` | ✅ | 错误处理：状态码映射、消息提取、showError |
| `storage.ts` | ✅ | localStorage 工具：`clearOtherUsersKeys` / `clearAllKeys` / `isExpired`（Pinia stores 共用） |
| `sanitize.ts` | ✅ | XSS 防护：HTML 转义、危险标签过滤 |

### src/types/ & src/graph/ & src/styles/

| 文件 | 状态 | 作用 |
|------|------|------|
| `types/index.ts` | ✅ | 全部 TypeScript 接口定义 |
| `graph/job_graph_repo.ts` | ✅ | 前端岗位图谱访问（Home/JobDetail 懒加载） |
| `styles/breakpoints.css` | ✅ | CSS 断点变量 |

---

## 已完成合并/删除文件（历史操作汇总）

| 操作 | 文件 | 说明 |
|------|------|------|
| 删除 | `app/services/resume_response.py` | 两个 Pydantic 模型移入 resume_service.py 末尾 |
| 删除 | `app/services/report_enhanced.py` | ReportEnhancer 类内联到 report_service.py |
| 删除（类） | `match_service_optimized.py::MatchResultCache` | 从未被调用（53行死代码） |
| 删除（类） | `match_service_optimized.py::MatchErrorHandler` | 从未被调用（40行死代码） |
| 删除（端点） | `GET /api/jobs` | 与 /api/match/jobs 完全相同，前端仅调用后者 |
| 删除（端点） | `GET /api/match/jobs/search` | 无前端调用 |
| 修复 | `match_service_optimized.py` | 补回 `import time`（被移除后导致运行时崩溃） |
| 删除 | `app/ai/prompts/*_v2.jinja2`（4个） | student_portrait / match_analysis / report_action_plan / chat_agent 的 v2 版本，从未被调用 |
| 删除 | `app/core/logging_config.py` | 从未被任何文件 import |
| 删除 | `app/data/complete_job_skills_db.py` | 从未被任何文件 import |
| 删除 | `app/data/skill_synonyms.py` | 从未被任何文件 import |
| 删除 | `app/data/resume_feature_engineer.py` | 从未被任何文件 import |
| 删除 | `app/data/data_cleaner.py` | 从未被任何文件 import |
| 删除 | `app/data/data_quality_monitor.py` | 从未被任何文件 import |
| 删除 | `app/services/precise_matcher.py` | 从未被 main.py 或任何服务 import |
| 删除 | `app/services/base.py` | BaseService 等从未被任何类继承 |
| 删除 | `app/services/interfaces.py` | 接口定义从未被实际使用 |
| 删除 | `app/services/__init__.py` | 仅导出 base/interfaces，随二者一并无用 |
| 删除 | `frontend/src/components/SkillGapAnalysis.vue` | 未被任何 view import |
| 删除 | `frontend/src/components/MatchSummaryCard.vue` | 未被任何 view import |
| 删除 | `frontend/src/components/MatchRadarChart.vue` | 未被任何 view import |
| 删除 | `frontend/src/utils/breakpoints.ts` | 未被任何文件 import |
| 删除 | `frontend/src/utils/lazy_load.ts` | 未被任何文件 import |
| 删除（类） | `app/ai/llm_client.py::FallbackLLMClient` | 多供应商降级链，改为单供应商直连 |
| 删除（方法） | `app/services/match_service.py::_score_qualities_potential_rule()` | 规则兜底降级，改为 LLM 失败直接抛异常 |
| 删除（方法） | `app/services/report_service.py::_fallback_action_plan()` | 行动计划规则兜底，改为 LLM 失败直接抛异常 |
| 删除（配置） | `app/config.py::LLM_FALLBACK_PROVIDERS` | 随 FallbackLLMClient 一并移除 |
| 删除（函数） | `frontend/src/api/crew.ts::runAnalysisWithFallback()` | 未使用的降级函数 |
| 移动 | `app/main.py → app/deps.py` | `_mask_sensitive` / `_mask_student_id` / `_mask_phone` / `_mask_email` 脱敏函数统一到 deps.py |
| 类型去重 | `frontend/src/types/index.ts` | 新增 MarketDemand/TransferPath/GapSkill/MatchDimension 等 8 个接口作为唯一定义源 |
| 清理 | `frontend/src/stores/useMatchStore.ts` | 移除游客假数据 / migrateGuestData / clearOtherUsersData |
| 清理 | `frontend/src/views/MatchAnalysis.vue` | 移除"AI分析服务临时降级"横幅和"规则降级"标签 |
