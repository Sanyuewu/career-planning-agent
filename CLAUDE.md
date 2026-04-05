# CLAUDE.md — 职业规划智能体项目工作指南

## 项目概览

**赛题定位**：面向高校学生的 AI 职业规划系统，核心流程：简历上传 → 学生画像 → 人岗匹配 → AI 对话 → 职业报告。

**技术栈**：
- 后端：FastAPI + SQLAlchemy async + SQLite (`data/career.db`)
- 前端：Vue 3 + Vite + Pinia + Arco Design（端口 5173）
- AI：单供应商 LLM（Groq/DeepSeek/Qwen 可选，直连无降级）+ CrewAI 多智能体
- 图谱：NetworkX 岗位知识图谱（`data/job_graph.json`，335节点/590边）
- crewai 1.12.2 已安装，多智能体工作流可用

---

## 目录结构

```
app/
  main.py                  # FastAPI 路由入口（Pydantic 模型在 schemas/api.py，认证守卫在 deps.py）
  deps.py                  # 共享依赖：get_current_user / require_role / audit_log / 脱敏工具
  config.py                # Settings（读 .env）
  constants.py             # 全局常量（DEGREE_MAP / WEIGHT_PRESETS / SKILL_SUGGESTIONS）
  schemas/
    api.py                 # API 请求/响应 Pydantic 模型（从 main.py 提取）
  services/
    resume_service.py          # 简历解析入口（PDF/DOCX/图片）+ ResumeParseResponse/ResumeUploadResponse 响应模型
    resume_enhanced.py         # 简历字段提取 & 质量评估（被 resume_service 引用）
    pdf_parser.py              # PDF/DOCX 文本提取（DocumentParser）
    portrait_service.py        # 学生画像计算
    job_graph_enhanced.py      # 岗位图谱增强（被 portrait_service 引用）
    match_service.py           # 人岗匹配（五维度，主流程）
    match_service_optimized.py # OptimizedSkillMatcher：多层技能匹配（被 match_service 引用）
    chat_agent_service.py      # AI 对话服务（9状态FSM + ReAct推理链 + 6工具 + 跨会话记忆 + SSE）
    report_service.py          # 报告生成（6章节 + LLM行动计划 + AI综合诊断 + ReportEnhancer 内联）
    report_export_service.py   # 报告导出（PDF/Word/HTML）
    recommend_service_optimized.py  # 推荐服务（懒加载于 /api/match/recommend）
    stats_service.py           # 用户统计（技能分/成就/竞争力历史）
    market_service.py          # 市场数据（行业趋势/学习资源）
    rag_service.py             # RAG 检索增强（JSON关键词降级检索，match_service 懒加载）
    job_fetcher.py             # 实时JD抓取（RemotiveAdapter + LocalGeneratorAdapter兜底）
  agents/
    crewai_agents.py       # CrewAI 代理定义
    crewai_config.py       # 代理配置
    crew_manager.py        # 多代理编排
    task_manager.py        # 任务管理
    crews/
      career_crew.py       # 职业规划工作流
    tools/
      __init__.py          # Agent 工具注册入口（crewai 1.12.2，CREWAI_TOOLS_AVAILABLE=True）
  graph/
    job_graph_repo.py      # 图谱访问（技能扩展/岗位查询）
  ai/
    llm_client.py          # 统一LLM客户端（单供应商直连 + llm_calibrator）
    llm_calibrator.py      # LLM 输出校准（被 llm_client 引用）
    embedding_service.py   # 文本嵌入服务
    prompts/               # Jinja2 提示词（6个 v1 模板）
  db/
    database.py            # SQLite 连接
    models.py              # ORM 模型（User/Student/Company/Match/Report/Chat）
    crud/                  # CRUD 操作（student/match/report/chat/portrait_history/job_real/job_trend/live_job/user_memory）
  data/
    job_skills_extended.py     # 技能扩展/同义词，被 match_service_optimized 引用
    industry_insights.py       # 8个行业深度洞察数据（growth_rate/hot_skills/hiring_seasons/competitive_ratio等），被 report_service 引用
    assessment_questions.py    # 三套题库（逻辑5题/职业倾向10题/技术自评5岗位×8题）+ 评分工具函数，被 /api/assessment 端点引用
  core/
    scheduler.py           # APScheduler 定时任务（每日JD抓取/趋势刷新）
  routers/
    agent.py               # CrewAI Agent API 路由（/api/agent/...）
    admin.py               # 管理员路由（/api/admin/...）
    company.py             # 企业路由（/api/company/...）
    assessment.py          # 测评路由（/api/assessment/...）
data/
  career.db              # SQLite 数据库
  job_graph.json         # 岗位图谱（335节点，590条边）
  job_profiles.json      # 51条岗位画像
  knowledge_base.json    # 本地知识库（30条条目，赛题提交材料①）
  reports/               # 导出报告缓存目录
frontend/src/
  views/                 # 页面组件（见下方路由表）
  stores/                # Pinia stores
  api/                   # 接口调用封装
  components/            # 可复用 UI 组件
  composables/           # Vue 组合式函数（useSSE/useECharts/useUpload）
  types/
    index.ts             # 全部 TypeScript 接口定义
  utils/
    error.ts             # 错误处理
    storage.ts           # localStorage 工具
    sanitize.ts          # XSS 防护
    breakpoints.ts       # 响应式断点
    lazy_load.ts         # 图片/组件懒加载
  graph/
    job_graph_repo.ts    # 前端岗位图谱（Home/JobDetail 页懒加载）
scripts/
  download_models.py     # 下载 embedding 模型（all-MiniLM-L6-v2）
models/
  all-MiniLM-L6-v2/      # 本地嵌入模型
```

---

## 启动方式

### 后端（必须用这种方式，否则热重载有 pycache 问题）

```bash
# 每次修改后端代码后执行：
find app -name "*.pyc" -delete
powershell -Command "Start-Process -FilePath '.venv\Scripts\python.exe' \
  -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000' \
  -WorkingDirectory 'D:\DPJ\claudde' \
  -RedirectStandardOutput 'D:\DPJ\claudde\backend.log' \
  -RedirectStandardError 'D:\DPJ\claudde\backend_err.log' \
  -WindowStyle Hidden"
```

### 前端

```bash
cd frontend && npm run dev   # 端口 5173
```

---

## 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/upload` | ResumeUpload.vue | 简历上传（核心入口） |
| `/portrait` | Portrait.vue | 学生画像 |
| `/match` | MatchAnalysis.vue | 人岗匹配 |
| `/chat` | ChatAdvisor.vue | AI 对话 |
| `/report` | CareerReport.vue | 职业报告 |
| `/assessment` | Assessment.vue | 三维度能力测评（新） |
| `/graph/:jobId?` | CareerGraph.vue | 岗位知识图谱 |
| `/jobs/:jobId` | JobDetail.vue | 职位详情 |
| `/login` | Login.vue | 登录/注册 |
| `/admin` | AdminDashboard.vue | 管理员面板（需 admin 权限） |
| `/company` | CompanyDashboard.vue | 企业面板（需 company 权限） |

**核心用户流程**：`/upload` → `/portrait` → `/match` → `/chat` → `/report`

---

## API 核心端点

### 核心五流程

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/resume/parse` | 文件上传（multipart，字段名 `file`） |
| POST | `/api/resume/parse-text` | 纯文本简历解析 |
| GET  | `/api/portrait/{student_id}` | 获取学生画像 |
| PUT  | `/api/portrait/{student_id}` | 更新画像（手动编辑） |
| POST | `/api/match/compute` | 人岗匹配（body: `{student_id, job_name}`） |
| GET  | `/api/match/jobs` | 获取岗位列表 |
| POST | `/api/report/generate` | 触发报告生成（query: `student_id`, `job_name`） |
| GET  | `/api/report/status/{task_id}` | 轮询报告状态 |
| GET  | `/api/report/{report_id}` | 获取报告详情 |
| POST | `/api/chat/session` | 创建对话 session（query: `student_id`） |
| POST | `/api/chat/stream` | 流式 AI 对话 |

### 报告导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/report/{report_id}/word` | 导出 Word |
| GET  | `/api/report/{report_id}/html` | 导出 HTML |
| GET  | `/api/report/{report_id}/pdf` | 导出 PDF |
| POST | `/api/report/{report_id}/polish` | AI 润色报告（可选 chapter_titles + feedback_hint，保存 pre_polish_snapshot） |
| POST | `/api/report/{report_id}/undo_polish` | 撤销润色（从 extra_data.pre_polish_snapshot 还原） |

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，返回 JWT |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET  | `/api/auth/me` | 当前用户信息 |

### 匹配扩展

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/match/history/{student_id}` | 匹配历史 |
| POST | `/api/match/batch` | 批量匹配 |
| GET  | `/api/match/recommend/{student_id}` | 个性化岗位推荐 |

### 画像扩展

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/portrait/{student_id}/history` | 画像历史 |
| GET  | `/api/portrait/{student_id}/skill_scores` | 技能得分 |
| GET  | `/api/portrait/{student_id}/competitiveness_history` | 竞争力历史 |
| GET  | `/api/portrait/{student_id}/score_detail` | 技能得分详情 |

### 岗位 & 市场

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/jobs/search` | 岗位搜索 |
| GET  | `/api/jobs/info` | 岗位信息 |
| GET  | `/api/jobs/ai_insight` | AI 岗位洞察（LLM 实时生成）|
| GET  | `/api/jobs/career-graph` | 岗位职业路径图 |
| GET  | `/api/jobs/real` | 真实 JD 数据 |
| GET  | `/api/jobs/live` | 实时抓取岗位列表 |
| GET  | `/api/jobs/live/stats` | 实时岗位均薪/数量统计 |
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
| GET  | `/api/user/{student_id}/achievements` | 用户成就 |
| GET  | `/api/recommend/learning_resources/{student_id}` | 学习资源推荐 |
| POST | `/api/feedback` | 提交反馈 |
| GET  | `/api/feedback/stats/{target_type}` | 反馈统计 |

### 对话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/chat/sessions` | session 列表（query: `student_id`） |
| GET  | `/api/chat/session/{session_id}` | session 详情 |
| DELETE | `/api/chat/session/{session_id}` | 删除 session |
| PATCH | `/api/chat/session/{session_id}` | 更新 session |
| POST | `/api/chat/message` | 普通消息（非流式） |
| GET  | `/api/chat/history/{session_id}` | 对话历史 |

### 报告管理

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT  | `/api/report/{report_id}` | 更新报告 |
| POST | `/api/report/{report_id}/adjust` | 章节/行动计划局部调整 |
| POST | `/api/report/{report_id}/feedback_optimize` | 基于反馈重新优化 |
| GET  | `/api/report/{report_id}/completeness` | 报告完整度 |
| GET  | `/api/report/{report_id}/quality` | 报告质量评分 |

### 认证扩展

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT  | `/api/auth/password` | 修改密码 |

### 企业端

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/PUT | `/api/company/profile` | 企业档案 |
| GET/POST | `/api/company/jobs` | 岗位列表/发布 |
| PUT  | `/api/company/jobs/{job_id}` | 更新岗位 |
| PUT  | `/api/company/jobs/{job_id}/status` | 更新岗位状态 |
| POST | `/api/company/reverse_match` | 反向匹配学生 |
| GET/POST/DELETE | `/api/company/saved_candidates` | 收藏候选人 |
| GET  | `/api/company/market_stats` | 市场统计 |

### 管理员端

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/admin/stats` | 系统统计 |
| GET/PUT/DELETE | `/api/admin/users` | 用户管理 |
| GET  | `/api/admin/hot_jobs` | 热门岗位 |
| GET  | `/api/admin/job_stats` | 岗位统计 |
| GET  | `/api/admin/logs` | 系统日志 |
| POST | `/api/admin/refresh_job_graph` | 刷新岗位图谱 |
| GET  | `/api/admin/user_trends` | 用户增长趋势 |
| GET  | `/api/admin/match_distribution` | 匹配分布 |
| GET  | `/api/admin/industry_stats` | 行业统计 |

### 能力测评

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/assessment/questions` | 获取题目（query: `job_hint`），返回 logic/career_tendency/tech_self_assessment 三套 |
| POST | `/api/assessment/submit` | 提交答案，body: `{student_id, answers: [{q_id, answer}], job_hint}`，返回分数 + 自动合并 ability_profile |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/debug/errors` | 错误日志（开发环境） |
| POST | `/api/debug/client-error` | 上报前端错误 |
| GET  | `/health` | 健康检查 |

---

## 关键已知问题和修复记录

### 1. `duration_months: null` 导致 sum() 崩溃
**根因**：`i.get("duration_months", 0)` 当值为 `None` 时不走默认值，仍返回 `None`。
**修复**：改为 `(i.get("duration_months") or 0)`。
**影响文件**：`match_service.py:281`、`report_service.py:103`、`portrait_service.py:78`

### 2. pycache 导致热重载失效
**根因**：uvicorn `--reload` 模式在中文路径下 WatchFiles 检测异常，`.pyc` 缓存不更新。
**修复**：每次改完代码后手动 `find app -name "*.pyc" -delete` 再重启。

### 3. 简历上传 422 错误
**根因**：`/api/resume/parse` 接口期望 `multipart/form-data`，字段名为 `file`。
**排查**：检查 ResumeUpload.vue 中 FormData 的字段名是否是 `file`。

### 4. Vite 代理端口
**必须是 8000**：`frontend/vite.config.ts` 中 `target: 'http://127.0.0.1:8000'`。

### 5. curl 被系统代理拦截
本机有 Clash（127.0.0.1:7897）拦截所有 curl 请求。
**绕过方式**：使用 Python socket 直连，或在代码中直接调用服务层测试。

---

## 调试流程

### 发现问题时告诉我：
1. **操作**：在哪个页面做了什么
2. **状态码**：F12 → Network → 红色请求 → 状态码（422/500/502）
3. **Response 内容**：点开失败请求的 Response 标签，复制错误文字
4. **文件信息**（上传类问题）：格式 + 大小

### 快速诊断后端错误：
```bash
# 查看后端访问日志（HTTP 请求记录）
cat backend.log

# 查看后端错误日志（每次重启会覆盖）
cat backend_err.log

# 实时滚动查看
tail -f backend_err.log

# 只看错误和警告行
grep -E "ERROR|WARNING|Exception|Traceback" backend_err.log

# 直接测试接口（绕过代理）
python -X utf8 -c "
import socket, json
s = socket.create_connection(('127.0.0.1', 8000), timeout=30)
body = json.dumps({...}).encode()
req = f'POST /api/xxx HTTP/1.1\r\nHost: 127.0.0.1:8000\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode() + body
s.sendall(req)
resp = b''
while True:
    chunk = s.recv(4096)
    if not chunk: break
    resp += chunk
s.close()
print(resp.decode(errors='replace')[:500])
"
```

---

## 数据模型要点

### StudentModel（数据库）字段均为 JSON 类型：
- `basic_info`：dict，含 name/school/major/grade
- `education`：list of dict，含 degree/school/major/gpa
- `internships`：list of dict，`duration_months` **可为 null**
- `skills`：list of str
- `inferred_soft_skills`：dict，score **可为 null**

### UserModel（认证）：
- `username` / `password_hash`（bcrypt）/ `role`（student/admin/company）
- JWT 认证，`get_current_user` 依赖内联于 `app/main.py`

### 常见 None 陷阱：
- `dict.get(key, default)` 在 value 为 `None` 时**不走 default**，应用 `or default`
- `student.xxx or []` 在 ORM 对象上安全，但序列化为 dict 后需注意

---

## 代码规范

- 所有业务常量从 `app/constants.py` 导入，不要 hardcode
- LLM 调用通过 `llm_client.chat_structured()` 或 `llm_client.chat()`
- Jinja2 提示词在 `app/ai/prompts/` 目录，用 `render_prompt()` 渲染
- 前端 API 调用统一在 `frontend/src/api/` 下，不要在组件里直接 axios
- **前端硬编码标签/选项统一存储在 `frontend/src/constants.ts`**，组件内不得内联定义重复的映射对象
- 修改图谱数据后需重新生成 `data/job_graph.json`
- **日志规范**：每个服务文件顶部声明 `logger = logging.getLogger(__name__)`；关键路径必须有 INFO 级别入口/出口日志（含耗时）；LLM 调用失败必须 WARNING/ERROR；DEBUG 级别用于细节（token数、字符数等）
- **前端 localStorage 工具**：`frontend/src/utils/storage.ts` 提供 `clearOtherUsersKeys` / `clearAllKeys` / `isExpired`，Pinia stores 统一调用，不得重复实现循环清理逻辑

---

## 前端工作方式

- Pinia stores：`useUserStore`（用户/认证）/ `useMatchStore`（匹配结果）/ `usePortraitStore`（画像缓存）/ `useReportStore`（报告状态）/ `useCrewStore`（多智能体状态）
- 路由守卫：未登录访问受保护页面自动跳转 `/login`，Token 过期提示重新登录
- 竞争力等级：后端返回 `A/B/C/D`，前端 `getLevelClass` 映射为 `excellent/good/normal/weak`
- 置信度 < 0.75 时前端显示"建议人工复核"警告横幅
- 流式对话：`useSSE.ts` 封装 SSE，`/api/chat/stream` 返回 `text/event-stream`
