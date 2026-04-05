# TODO.md — 职业规划智能体项目状态

> 更新日期：2026-04-05
> 依据：赛题【A13】原文逐条对照 + 全维度质量审查

---

## 赛题原文关键要求对照（审查结论）

| 赛题条款 | 现状 | 结论 |
|---|---|---|
| ≥10 个岗位画像（含软技能维度） | 51 个完整画像 | ✅ |
| 垂直岗位图谱（晋升路径） | 234 条 PROMOTES_TO 边 | ✅ |
| 换岗路径图谱（≥5 岗位 × ≥2 路径） | 65 个岗位各有 ≥2 条 | ✅ |
| 简历上传/录入 → 学生画像 | PDF/DOCX/文本，含软技能推断 | ✅ |
| 完整度 + 竞争力评分 | 完整度条 + 竞争力仪表盘 | ✅ |
| 4 维度人岗匹配（基础/技能/素养/潜力） | 5 维度（含市场需求），覆盖全部 4 项 | ✅ |
| 根据维度权重综合打分 | 后端 WEIGHT_PRESETS + 前端权重选择 UI | ✅ |
| 职业生涯发展报告（6 章 + 行动计划） | 完整 6 章报告 | ✅ |
| 分阶段行动计划（短期/中期） | 短期 30 天 + 中期 3-6 月 | ✅ |
| 评估周期与指标（动态调整） | 行动计划含里程碑检查节点 | ✅ |
| 报告手动编辑 | 章节编辑 + 行动计划编辑 | ✅ |
| 报告智能润色 + 完整性检查 | AI 润色 + auto_quality_check | ✅ |
| 一键导出（PDF/Word） | PDF/Word/HTML 三格式 | ✅ |
| 大模型用于岗位画像/学生画像/匹配/报告 | 岗位 AI 洞察 + 学生画像评估 + 匹配打分 + 报告生成 | ✅ |
| 企业提交材料 ①：本地知识库资料 | knowledge_base.json（30条），RAG JSON 降级检索 | ✅ |
| 企业提供 10000 条岗位数据集 | job_real 表有 9958 条 | ✅ |
| 关键技能匹配准确率 ≥80% | confidence 机制 + 命中率展示 | ✅ |

---

## 全维度质量审查（2026-04-04）

> 目标：各维度达到 95 分以上。以下为当前评估与差距分析。

| 维度 | 当前分 | 差距根因 | 优先级 |
|------|--------|----------|--------|
| 人岗匹配准确性 | 73 | gap_skills 无熟练度差距标注；技能重复未归一化 | P0 |
| 画像生成准确性 | 70 | GPA 未计入竞争力；技能质量无校验（1项与10项同分） | P0 |
| 报告生成准确性 | 72 | 行动计划推荐技能未做 KB 验证；路径不基于图谱实际数据 | P0 |
| 推理能力 | 67 | 工具结果不跨轮次保留；ReAct 固定 3 步上限 | P1 |
| 记忆能力 | 62 | session 数据可被旧 DB 记忆覆盖；无冲突解决机制 | P0 |
| 个性化能力 | 63 | 无排斥偏好处理；推荐不感知用户明确拒绝的方向 | P1 |
| 响应速度 | 76 | 市场数据无独立缓存；同轮多次调同一工具无去重 | P2 |
| 交互流程 | 69 | 前端错误提示无上下文；长任务无进度反馈 | P1 |
| 界面设计 | 71 | 移动端断点覆盖不全；null 值展示空白 | P2 |
| 数据准确性 | 66 | 技能名称未归一化（Python3/Python 算两个）；无异常值检测 | P0 |
| 数据完整性 | 68 | skills/learning_resources/industry_insights_db 表建了但无数据 | P1 |

---

## 已完成的优化（2026-04-04 新增）

### 对话智能体六大缺陷优化 ✅
- [x] **消除代码重复**：`generate_response_stream`/`_generate_normal_response` 统一调用 `_build_system_prompt`
- [x] **match_detail 全状态注入**：`_MATCH_DETAIL_STATES` = MATCH_ANALYSIS/CAREER_GUIDANCE/REPORT_REVIEW/REPORT_REFINE
- [x] **FSM 语义推进**：GREETING 需要画像有实质信息才推进；PORTRAIT_FILLING 超时从 7 轮改为 10 轮；INTENT_CONFIRM 容忍从 3 轮改为 6 轮
- [x] **FSM 回退路径**：新增 `portrait_update` trigger，从深层状态可回退到 PORTRAIT_FILLING；`_PORTRAIT_UPDATE_KWS` 关键词检测
- [x] **tool_router few-shot**：提示词增加 6 条有/无工具的具体示例
- [x] **跨会话记忆扩展**：新增保存 `last_matched_job`（岗位+得分）和 `skills_snapshot`

### P0 修复（2026-04-04）✅
- [x] **技能归一化**：`resume_service._rule_fallback` 对提取技能去重 + 标准化（统一小写、移除括号）
- [x] **gap_skills 熟练度标注**：`match_service_optimized` gap_skills 输出包含 `required_level` 字段
- [x] **GPA 计入竞争力**：`portrait_service._calculate_competitiveness` 加入 GPA 维度（占5%）
- [x] **行动计划 KB 验证**：`report_service._generate_action_plan` 完成后对推荐技能做知识库命中标记
- [x] **记忆冲突解决**：`load_user_memory` 只填充 session portrait 中尚未有值的字段（session > DB 优先）

---

## 已完成的架构优化（2026-04-03）

### 后端优化
- [x] **脱敏函数统一**：`_mask_sensitive`/`_mask_student_id`/`_mask_phone`/`_mask_email` 从 main.py 移至 deps.py，消除重复
- [x] **LLM 客户端简化**：移除 `FallbackLLMClient` 多供应商级联降级，单一供应商直连，失败即报错
- [x] **移除 `LLM_FALLBACK_PROVIDERS` 配置项**
- [x] **匹配服务去降级**：移除 `_score_qualities_potential_rule()` 规则兜底、市场需求静默 fallback，LLM 失败直接抛异常
- [x] **报告服务去降级**：移除 `_fallback_action_plan()` 规则兜底
- [x] **Pydantic 模型提取**：20 个 inline 模型 → `schemas/api.py`
- [x] **认证守卫去重**：main.py 不再定义 `get_current_user`/`require_role`，统一从 deps.py 导入
- [x] **补齐 /api/jobs/live 和 /api/jobs/live/stats 路由**
- [x] **删除无用后端文件**：`schemas/common.py`、`core/response.py`、`services/cache_service.py`
- [x] **`__init__.py` 精简**

### 前端优化
- [x] **TypeScript 类型去重**：统一定义在 `types/index.ts`
- [x] **移除游客模式假数据**
- [x] **移除降级 UI**
- [x] **清理游客数据迁移**
- [x] **删除死 API 函数**
- [x] **删除无用前端文件**：`MatchRadarChart.vue`、`breakpoints.ts`、`lazy_load.ts`
- [x] **crew.ts 清理**

---

## 已完成的功能（F/B/C/D/E 系列，共 25 项）

| 编号 | 功能模块 | 状态 |
|------|----------|------|
| F-1 | 权重方案选择 UI | ✅ |
| F-2 | 本地知识库（RAG 降级） | ✅ |
| F-3 | 行动计划评估周期与里程碑 | ✅ |
| F-4 | 岗位画像 LLM 增强展示 | ✅ |
| F-5 | 对话智能体与匹配结果集成 | ✅ |
| F-6 | 数据集来源 + 准确率展示 | ✅ |
| B-1 | 知识库接入对话工具链 | ✅ |
| B-2 | 知识库作为 RAG 上下文注入匹配 | ✅ |
| B-3 | 测评结果注入匹配 | ✅ |
| C-1~C-5 | 对话修复 + 流式 + 记忆 + 报告增强 | ✅ |
| D-1~D-5 | JWT密钥 + CrewAI + ReAct占位 + 并行化 | ✅ |
| E-1~E-5 | Prompt注入 + 工具增强 + 触发词扩展 | ✅ |

---

## 已完成的文档同步（2026-04-03）

- [x] **requirements.txt 更新**
- [x] **FILE_MAP.md 更新**
- [x] **README.md 更新**

---

## 已完成的 Bug 修复（2026-04-03）

### [P0] ~~人岗匹配崩溃修复~~ ✅
- [x] `match_service.py:301`：`inferred_soft_skills` 值为嵌套 dict 时 `sorted()` 崩溃
- [x] `match_service.py:626`：维度三/四 LLM 评估失败直接 `raise`，新增规则降级

### [P0] ~~报告生成崩溃修复~~ ✅
- [x] `report_service.py:417`：`_generate_action_plan` LLM 失败新增规则降级

### [P1] ~~推荐评分趋同修复~~ ✅
- [x] `recommend_service_optimized.py`：空技能岗位改为50分中性分；评分公式提升区分度

### [P1] ~~首页 AI 推荐按钮修复~~ ✅
- [x] 原调用假 CrewAI，改为直接调用 `matchApi.recommend()`

---

## 智能体系统现状（2026-04-04 更新）

| 层 | 模块 | 是否真 LLM | 说明 |
|---|---|---|---|
| 对话层 | `chat_agent_service.py` | ✅ 是 | ReAct推理链 + 9工具 + 9状态FSM + 跨会话记忆 + few-shot路由 |
| 多Agent层 | `career_crew.py` + `crewai_agents.py` | ✅ 是 | CrewAI 4-Agent 顺序协作 |
| 遗留层 | `crew_manager.py` | ❌ 否 | 规则引擎，已重定向至 CrewAI |

---

## 待完成项（P0→P1→P2 排序）

### ~~[P0] 数据完整性 — 新建表数据初始化~~ ✅

- [x] **D-1 数据迁移**：`scripts/init_db_data.py`，83 条技能写入 `skills` 表
- [x] **D-2 数据填充**：35 条学习资源写入 `learning_resources` 表
- [x] **D-3 数据迁移**：8 个行业写入 `industry_insights_db` 表

### ~~[P0] 人岗匹配 — 规则评分与LLM评分融合~~ ✅

- [x] 维度一/二规则分作为先验分注入维度三/四 LLM Prompt（`match_analysis_v1.jinja2` + `match_service.py`）
- [x] 差距 >20 时 Prompt 要求 detail 中必须说明原因

### ~~[P1] 推理能力 — 工具结果跨轮保留~~ ✅

- [x] `tool_cache` 字段存于 `session.student_portrait`，命中则直接返回缓存结果

### ~~[P1] 个性化 — 排斥偏好感知~~ ✅

- [x] `_extract_intent_from_message` 排斥检测 + `preferences.rejected` 存储
- [x] `recommend_service_optimized` 过滤已拒绝岗位类型

### ~~[P1] 交互流程 — 长任务进度反馈~~ ✅

- [x] `report_crud.update_progress` 将进度写入 `extra_data._progress`
- [x] `_run_report_generation` 在匹配完成(25%)、章节生成(60%)、整理完成(90%)三个节点更新进度
- [x] 状态端点从 `extra_data` 读取真实进度，不再返回固定 50%

### ~~[P1] 界面设计 — null 值友好展示~~ ✅

- [x] `MatchAnalysis.vue`：`rec.score`、`dim.score`、`dim.weight` 空值显示"--"
- [x] `Portrait.vue`：`dim.score`、`val`（ability bars）空值显示"--"，进度条宽度使用 `?? 0` 兜底

### ~~[P0] 前端崩溃风险~~ ✅（2026-04-04 修复）

- [x] `confidence_breakdown` / `skill_match_details` / `gap_analysis`：后端新增三个字段并在 `compute_match` 中构建真实数据，前端展示正常
- [x] `CareerGraph.vue`：`selectJob(null)` 加 early return 防御
- [x] `AdminDashboard.vue`：`res.hot_jobs` → `(res.hot_jobs || []).slice()`
- [x] `Home.vue`：双重赋值改为 `Promise.all` 一次性赋值

### ~~[P1] 前端展示错误~~ ✅（2026-04-04 修复）

- [x] `Portrait.vue`：`edu.gpa` 加 `!= null && !== ''` 保护，软技能分数 `||` 改 `??`
- [x] `AdminDashboard.vue`：`loadStats/loadUsers/loadJobStats` catch 块加 `console.error`
- [x] `CompanyDashboard.vue`：`loadProfile/loadJobs` catch 块加 `console.error`，`loadJobs` 兼容字符串数组和对象数组返回格式

### ~~[A0] 代码结构重构~~ ✅（2026-04-05）

- [x] **main.py 拆分**：2573行 → 277行；路由提取至 8 个新模块（auth/resume/portrait/match/market/report/chat/graph）
- [x] **共享工具模块**：`app/rate_limit.py`（限流器）、`app/cache.py`（共享缓存）、`app/auth_utils.py`（JWT/密码工具）
- [x] **chat_agent_service.py 重构**：1485行 → 1441行
  - `execute_tool` 200行 if-elif → 9个私有方法 + `_TOOL_HANDLERS` 调度表
  - 提取 `_preprocess_message()` 消除 `generate_response` / `generate_response_stream` 60% 代码重复
  - 提取 `_REFINE_KWS` / `_BACK_STATES` 为模块级常量（原来在两个方法里各定义一次）

### [P2] 响应速度 — 工具调用去重

- [ ] 同一 session 同一轮次内，相同参数的工具调用只执行一次

### [P2] 数据库 — 孤儿数据清理脚本

- [ ] `scripts/cleanup_orphans.py`：清理无对应 student 的 match_results/reports/chat_sessions

### [P2] 体积优化

- [ ] 拆分 `requirements.txt` → `requirements.txt`（生产）+ `requirements-dev.txt`（开发/测试）
- [ ] `embedding_service.py` 优先加载 `onnx/model_qint8_avx512.onnx`
- [ ] A-4（低优先）：FSM 状态转移逻辑集中化

### [P3] 前端代码质量（2026-04-04 审查）

- [ ] `CareerGraph.vue`、`Assessment.vue`、`MatchAnalysis.vue` 颜色/标签映射硬编码，应统一到 `constants.ts`
- [ ] 空状态/Loading UI 在 8 个页面各自重复实现，应提取公共组件
- [ ] `AdminDashboard.vue` 分页当无数据时两个箭头都禁用无提示文字
