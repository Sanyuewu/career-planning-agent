# AI 职业规划智能体

面向高校学生的智能职业规划系统。核心流程：简历上传 → 学生画像构建 → 人岗匹配（五维度）→ AI 对话顾问 → 职业发展报告生成与导出。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + SQLAlchemy (async) + SQLite |
| 前端 | Vue 3 + Vite + Pinia + Arco Design + ECharts |
| AI | 单供应商 LLM（DeepSeek / Qwen / Groq 任选其一）+ CrewAI 多智能体 |
| 图谱 | NetworkX 岗位知识图谱（335 节点 / 590 边） |

## 目录结构

```
├── app/
│   ├── main.py              # FastAPI 主入口（含全部路由）
│   ├── deps.py              # 共享依赖（JWT 认证守卫 + 脱敏工具）
│   ├── config.py            # Settings（读 .env）
│   ├── constants.py         # 全局常量
│   ├── routers/
│   │   └── agent.py         # CrewAI Agent 路由
│   ├── services/            # 业务逻辑
│   │   ├── resume_service.py        # 简历解析主入口
│   │   ├── resume_enhanced.py       # 简历字段提取 & 质量评估
│   │   ├── pdf_parser.py            # PDF/DOCX/图片文本提取
│   │   ├── portrait_service.py      # 学生画像计算
│   │   ├── job_graph_enhanced.py    # 岗位图谱增强查询
│   │   ├── match_service.py         # 人岗匹配（五维度主流程）
│   │   ├── match_service_optimized.py  # OptimizedSkillMatcher
│   │   ├── chat_agent_service.py    # AI 对话（九状态 FSM + ReAct + SSE）
│   │   ├── report_service.py        # 职业报告生成（六章节 + LLM 行动计划）
│   │   ├── report_export_service.py # 报告导出 Word/HTML/PDF
│   │   ├── recommend_service_optimized.py  # 个性化岗位推荐
│   │   ├── stats_service.py         # 用户统计
│   │   ├── market_service.py        # 市场数据 & 行业趋势
│   │   ├── rag_service.py           # RAG 检索增强（JSON 降级检索）
│   │   └── job_fetcher.py           # 实时 JD 抓取（Remotive + 本地生成兜底）
│   ├── agents/              # CrewAI 多智能体
│   │   ├── crewai_agents.py
│   │   ├── crewai_config.py
│   │   ├── crew_manager.py
│   │   ├── task_manager.py
│   │   └── crews/career_crew.py
│   ├── graph/
│   │   └── job_graph_repo.py    # 岗位知识图谱访问
│   ├── ai/
│   │   ├── llm_client.py        # 统一 LLM 客户端（单供应商直连）
│   │   ├── llm_calibrator.py    # LLM 输出后处理
│   │   ├── embedding_service.py # 文本向量化
│   │   └── prompts/             # 6 个 Jinja2 提示词（v1）
│   ├── db/
│   │   ├── models.py        # ORM 模型
│   │   └── crud/            # CRUD 操作（student/match/report/chat/portrait_history
│   │                        #           /job_real/job_trend/live_job/user_memory）
│   ├── schemas/
│   │   └── api.py           # API 请求/响应 Pydantic 模型（20 个类）
│   ├── data/
│   │   ├── job_skills_extended.py   # 技能扩展/同义词
│   │   ├── industry_insights.py     # 8 个行业深度洞察数据
│   │   └── assessment_questions.py  # 三套题库（逻辑/职业倾向/技术自评）
│   └── core/
│       └── scheduler.py     # APScheduler 定时任务（每日 JD 抓取 / 趋势刷新）
├── frontend/src/
│   ├── views/               # 页面组件（11个）
│   ├── stores/              # Pinia stores（5个）
│   ├── api/                 # 接口封装（10个）
│   ├── components/          # 可复用组件（21个）
│   ├── composables/         # useSSE / useECharts / useUpload
│   ├── types/index.ts       # TypeScript 接口定义
│   ├── constants.ts         # 前端全局常量
│   └── utils/               # error / sanitize / storage / breakpoints / lazy_load
├── data/
│   ├── career.db             # SQLite 数据库
│   ├── job_graph.json        # 岗位图谱（335节点，590条边）
│   ├── job_profiles.json     # 51个岗位画像
│   ├── knowledge_base.json   # 本地知识库（30条岗位知识条目，RAG检索用）
│   └── reports/              # 导出报告缓存目录（Word/HTML/PDF）
├── models/
│   └── all-MiniLM-L6-v2/   # 本地嵌入模型
└── scripts/
    └── download_models.py   # 下载嵌入模型
```

## 环境要求

- Python 3.12+
- Node.js 20+

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填写 LLM API Key：

```ini
# 使用 Groq（推荐，免费额度充足）
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key

# 或使用 DeepSeek
LLM_PROVIDER=deepseek
LLM_API_KEY=your_deepseek_api_key

# JWT 密钥（生产环境必须修改）
JWT_SECRET=your-random-secret-key-at-least-32-chars
```

### 2. 安装依赖

```bash
# 后端
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt

# 下载预训练模型（用于文本嵌入）
python scripts/download_models.py

# 前端
cd frontend && npm install
```

### 3. 启动服务

#### 后端（Windows）

每次修改后端代码后执行（避免 pycache 热重载问题）：

```bash
# 清理字节码缓存
find app -name "*.pyc" -delete

# 后台启动 uvicorn，日志写入文件
powershell -Command "Start-Process -FilePath '.venv\Scripts\python.exe' \
  -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000' \
  -WorkingDirectory 'D:\DPJ\claudde' \
  -RedirectStandardOutput 'D:\DPJ\claudde\backend.log' \
  -RedirectStandardError 'D:\DPJ\claudde\backend_err.log' \
  -WindowStyle Hidden"
```

#### 前端

```bash
cd frontend && npm run dev
```

访问 **http://localhost:5173**，API 文档：**http://localhost:8000/docs**

### 4. 查看日志

```bash
# 查看后端访问日志（HTTP 请求记录）
cat backend.log

# 查看后端错误日志（启动错误、异常、警告）
cat backend_err.log

# 实时滚动查看错误日志
tail -f backend_err.log

# 只看错误和警告行
grep -E "ERROR|WARNING|Exception|Traceback" backend_err.log

# 查看前端构建日志
cat frontend.log
```

> **注意**：每次重启后端，`backend.log` 和 `backend_err.log` 会被覆盖。

## 演示账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 学生 | `demo_student` | `demo123` |
| 企业 | `demo_company` | `demo123` |
| 管理员 | `admin` | `admin123456` |

## 核心功能

### 学生画像
- PDF/DOCX/图片简历解析（LLM 结构化提取）
- 手动录入引导表单
- 教育、技能、实习、项目、证书、奖项六维信息
- 竞争力评分（A/B/C/D）+ 软技能评估

### 人岗匹配（五维度）
1. 基本要求（学历/专业）
2. 专业技能（must_have / nice_to_have + 语义相似匹配）
3. 职业素质（软技能评估）
4. 发展潜力（学习能力/项目经历）
5. 市场需求（真实 JD 数量/薪资数据）

### 职业发展报告
- 六章 AI 生成报告
- 短期（30天）+ 中期行动计划
- PDF / Word / HTML 导出

### AI 对话顾问
- 九状态 FSM（GREETING / PORTRAIT_FILLING / INTENT_CONFIRM / MATCH_ANALYSIS / CAREER_GUIDANCE / EMOTION_SUPPORT / REPORT_REVIEW / REPORT_REFINE / END）
- ReAct 推理链：Thought → Action（6种工具）→ Observation → Answer
- 跨会话长期记忆（UserMemoryModel 持久化）
- 情绪感知 + 情绪支持分支
- 真实流式输出（SSE）
- LLM 单供应商直连（DeepSeek / Qwen / Groq 任选）

### 职业图谱
- 335 节点（225 岗位 + 146 技能）
- 晋升路径 / 换岗路径 / 技能关联
- ECharts 交互可视化

### 能力测评
- 逻辑推理（5题）/ 职业倾向（10题）/ 技术自评（5岗位×8题）
- 测评结果自动同步到学生画像（ability_profile）

## 完整 API

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，返回 JWT |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET  | `/api/auth/me` | 当前用户信息 |
| PUT  | `/api/auth/password` | 修改密码 |

### 核心五流程

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/resume/parse` | 文件上传（multipart，字段名 `file`） |
| POST | `/api/resume/parse-text` | 纯文本简历解析 |
| GET  | `/api/portrait/{student_id}` | 获取学生画像 |
| PUT  | `/api/portrait/{student_id}` | 更新画像 |
| GET  | `/api/portrait/{student_id}/history` | 画像历史 |
| GET  | `/api/portrait/{student_id}/skill_scores` | 技能得分 |
| GET  | `/api/portrait/{student_id}/competitiveness_history` | 竞争力历史 |
| POST | `/api/match/compute` | 人岗匹配（body: `{student_id, job_name}`） |
| GET  | `/api/match/jobs` | 获取岗位列表 |
| GET  | `/api/match/history/{student_id}` | 匹配历史 |
| POST | `/api/match/batch` | 批量匹配 |
| GET  | `/api/match/recommend/{student_id}` | 个性化岗位推荐 |
| POST | `/api/report/generate` | 触发报告生成（query: `student_id`, `job_name`） |
| GET  | `/api/report/status/{task_id}` | 轮询报告状态 |
| GET  | `/api/report/{report_id}` | 获取报告详情 |
| PUT  | `/api/report/{report_id}` | 更新报告 |
| GET  | `/api/report/{report_id}/completeness` | 报告完整度评估 |
| POST | `/api/chat/session` | 创建对话 session |
| GET  | `/api/chat/sessions` | 获取 session 列表 |
| GET  | `/api/chat/session/{session_id}` | 获取 session 详情 |
| DELETE | `/api/chat/session/{session_id}` | 删除 session |
| PATCH | `/api/chat/session/{session_id}` | 更新 session |
| POST | `/api/chat/message` | 普通消息（非流式） |
| POST | `/api/chat/stream` | 流式 AI 对话（SSE） |
| GET  | `/api/chat/history/{session_id}` | 对话历史 |

### 报告导出 & 操作

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/report/{report_id}/word` | 导出 Word |
| GET  | `/api/report/{report_id}/html` | 导出 HTML |
| GET  | `/api/report/{report_id}/pdf` | 导出 PDF |
| POST | `/api/report/{report_id}/polish` | AI 润色报告（可选 chapter_titles + feedback_hint）|
| POST | `/api/report/{report_id}/undo_polish` | 撤销润色（从 pre_polish_snapshot 还原）|
| POST | `/api/report/{report_id}/adjust` | 报告内容调整（章节/行动计划局部修改）|
| POST | `/api/report/{report_id}/feedback_optimize` | 基于反馈重新优化报告 |
| GET  | `/api/report/{report_id}/completeness` | 报告完整度评估 |
| GET  | `/api/report/{report_id}/quality` | 报告质量评分 |

### 岗位 & 市场

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/jobs/search` | 岗位搜索 |
| GET  | `/api/jobs/info` | 岗位信息 |
| GET  | `/api/jobs/ai_insight` | AI 岗位洞察（LLM 实时生成，100-200字）|
| GET  | `/api/jobs/career-graph` | 岗位职业路径图 |
| GET  | `/api/jobs/real` | 真实 JD 数据 |
| GET  | `/api/jobs/live` | 实时岗位列表（分页 + 筛选） |
| GET  | `/api/jobs/live/stats` | 实时岗位统计（各岗位 JD 数 + 均薪） |
| GET  | `/api/market/trends` | 行业趋势 |
| GET  | `/api/market/trend` | 市场趋势 |
| GET  | `/api/market/real_jobs` | 真实岗位数据 |
| GET  | `/api/market/industry_trends` | 行业趋势统计 |
| GET  | `/api/market/salary_comparison` | 岗位薪资对比 |
| GET  | `/api/graph` | 知识图谱数据 |
| GET  | `/api/graph/main-transfers/{job_name}` | 岗位主要转换路径 |

### 统计 & 推荐

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/stats/public` | 公开统计数据 |
| GET  | `/api/stats/user/{student_id}` | 用户统计 |
| GET  | `/api/portrait/{student_id}/score_detail` | 技能得分详情 |
| GET  | `/api/user/{student_id}/achievements` | 用户成就 |
| GET  | `/api/recommend/learning_resources/{student_id}` | 学习资源推荐 |
| POST | `/api/feedback` | 提交反馈 |
| GET  | `/api/feedback/stats/{target_type}` | 反馈统计 |

### 能力测评

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/assessment/questions` | 获取题目（query: `job_hint`），返回三套题 |
| POST | `/api/assessment/submit` | 提交答案，自动合并 ability_profile 到画像 |

### 企业端

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/company/profile` | 企业档案 |
| PUT  | `/api/company/profile` | 更新企业档案 |
| GET  | `/api/company/jobs` | 企业岗位列表 |
| POST | `/api/company/jobs` | 发布岗位 |
| PUT  | `/api/company/jobs/{job_id}` | 更新岗位 |
| PUT  | `/api/company/jobs/{job_id}/status` | 更新岗位状态 |
| POST | `/api/company/reverse_match` | 反向匹配学生 |
| GET  | `/api/company/saved_candidates` | 收藏候选人列表 |
| POST | `/api/company/saved_candidates` | 收藏候选人 |
| DELETE | `/api/company/saved_candidates/{student_id}` | 取消收藏 |
| GET  | `/api/company/market_stats` | 市场统计 |

### 管理员端

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/admin/stats` | 系统统计 |
| GET  | `/api/admin/users` | 用户列表 |
| PUT  | `/api/admin/users/{username}/role` | 修改用户角色 |
| DELETE | `/api/admin/users/{username}` | 删除用户 |
| GET  | `/api/admin/hot_jobs` | 热门岗位 |
| GET  | `/api/admin/job_stats` | 岗位统计 |
| GET  | `/api/admin/logs` | 系统日志 |
| POST | `/api/admin/refresh_job_graph` | 刷新岗位图谱 |
| GET  | `/api/admin/user_trends` | 用户增长趋势 |
| GET  | `/api/admin/match_distribution` | 匹配分布 |
| GET  | `/api/admin/industry_stats` | 行业统计 |

### CrewAI 多智能体（`/api/agent/...`）

详见 `app/routers/agent.py`。

### 调试（开发环境）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/debug/errors` | 错误日志查询 |
| POST | `/api/debug/client-error` | 上报前端错误 |
| GET  | `/health` | 健康检查 |

## 许可证

MIT License
