<template>
  <div class="report-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">
        <span>←</span>
      </button>
      <div class="header-content">
        <h1>职业报告</h1>
        <p>个性化职业发展规划</p>
      </div>
    </div>
    <StepProgress />

    <!-- O4-c: 空状态 -->
    <div v-if="!userStore.studentId" class="empty-state-page">
      <div class="empty-state-icon">📋</div>
      <h2>先完成匹配分析再生成报告</h2>
      <p>需要先上传简历并完成人岗匹配，系统才能生成职业规划报告</p>
      <a-button type="primary" @click="$router.push('/match')">前往匹配分析</a-button>
    </div>

    <div class="report-container" v-if="userStore.studentId">
      <div class="generate-section" v-if="reportStore.status === 'idle'">
        <div class="card">
          <h3>生成职业规划报告</h3>
          <p class="hint">选择目标岗位，AI将为您生成详细的职业发展规划报告</p>
          
          <div class="form-group">
            <label>目标岗位</label>
            <div class="job-select">
              <input 
                v-model="targetJobName" 
                placeholder="输入或选择目标岗位..."
                @focus="showJobList = true"
              />
              <div class="job-dropdown" v-if="showJobList && filteredJobs.length">
                <div 
                  class="job-option" 
                  v-for="job in filteredJobs" 
                  :key="job"
                  @click="selectJob(job)"
                >
                  {{ job }}
                </div>
              </div>
            </div>
          </div>
          
          <button 
            class="primary-btn" 
            @click="generateReport"
            :disabled="!targetJobName"
          >
            <span>🚀</span> 生成报告
          </button>
        </div>
      </div>

      <div class="progress-section" v-else-if="reportStore.status === 'pending' || reportStore.status === 'generating'">
        <div class="card">
          <h3>正在生成报告...</h3>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: reportStore.progress + '%' }"></div>
          </div>
          <p class="progress-text">{{ reportStore.progressMsg || 'AI正在分析中...' }}</p>
          <p class="progress-hint">通常需要 30-60 秒，请耐心等待</p>
          <button class="cancel-btn" @click="confirmCancel">取消</button>
        </div>
      </div>

      <div class="error-section" v-else-if="reportStore.status === 'failed'">
        <div class="card error-card">
          <div class="error-icon">⚠️</div>
          <h3>生成失败</h3>
          <p>{{ reportStore.error || '请重试' }}</p>
          <button class="primary-btn" @click="reportStore.clearReport()">重新生成</button>
        </div>
      </div>

      <div class="report-content" v-else-if="reportStore.status === 'done' && reportStore.reportContent">
        <!-- 标题栏 -->
        <div class="report-title-strip card">
          <div class="report-title-row">
            <div class="report-title-left">
              <h2>{{ reportStore.reportContent.jobName }}</h2>
              <span class="report-badge">职业发展报告</span>
              <span v-if="completenessResult" class="completeness-score-tag" :class="completenessResult.is_complete ? 'score-ok' : 'score-warn'">
                📋 {{ completenessResult.completeness_score }}分
              </span>
            </div>
            <div class="report-title-right">
              <span class="ai-disclaimer-inline">AI生成，仅供参考</span>
              <span class="report-date">{{ formatDate(reportStore.reportContent.createdAt) }}</span>
            </div>
          </div>
        </div>

        <!-- 警告条（仅在有警告时显示） -->
        <div class="alert-strip" v-if="(reportStore.reportContent.confidence != null && reportStore.reportContent.confidence < 0.75) || completenessWarnings.length">
          <div
            v-if="reportStore.reportContent.confidence != null && reportStore.reportContent.confidence < 0.75"
            class="alert-item alert-warn"
          >
            ⚠️ 置信度较低（{{ ((reportStore.reportContent.confidence ?? 0) * 100).toFixed(0) }}%），建议补充简历信息后重新生成
          </div>
          <div v-if="completenessWarnings.length" class="alert-item alert-info">
            📋 {{ completenessWarnings.join(' · ') }}
          </div>
        </div>

        <!-- 操作工具栏 -->
        <div class="report-toolbar card">
          <div class="toolbar-main">
            <div class="toolbar-group">
              <button class="action-btn" :class="{ active: isEditing }" @click="toggleEditMode" :disabled="saving">
                <span>{{ saving ? '⏳' : (isEditing ? '✓' : '✏️') }}</span>
                {{ saving ? '保存中...' : (isEditing ? '保存' : '编辑') }}
              </button>
              <button class="action-btn" :disabled="exportingPdf" @click="exportPdf">
                <span>📑</span> {{ exportingPdf ? '准备中...' : '导出PDF' }}
              </button>
              <button class="action-btn" :disabled="exportingWord" @click="exportWord">
                <span>📄</span> {{ exportingWord ? '准备中...' : '导出Word' }}
              </button>
            </div>
            <div class="toolbar-group">
              <button
                class="action-btn polish-btn"
                :disabled="isPolishing || polishingChapters"
                @click="polishReport"
              >
                <span>✨</span>
                {{ polishingChapters ? '润色中...' : 'AI润色' }}
              </button>
              <button
                class="action-btn undo-btn"
                v-if="canUndo"
                :disabled="undoing"
                @click="undoPolish"
              >
                {{ undoing ? '回滚中...' : '↩ 撤销' }}
              </button>
            </div>
            <div class="toolbar-group toolbar-right">
              <button class="action-btn" @click="$router.push('/chat')">
                <span>💬</span> 咨询AI
              </button>
              <button class="action-btn primary" @click="$router.push('/match')">
                <span>🎯</span> 继续匹配
              </button>
              <button class="action-btn danger-btn" @click="confirmNewReport">
                <span>🔄</span> 新报告
              </button>
            </div>
          </div>
          <FeedbackWidget
            v-if="reportStore.reportId"
            target-type="report"
            :target-id="reportStore.reportId"
            @low-rating="handleLowRating"
          />
        </div>

        <div class="score-overview card">
          <h3>综合评估</h3>
          <div class="overview-charts">
            <div class="gauge-wrap">
              <div ref="gaugeRef" class="gauge-chart"></div>
            </div>
            <div class="radar-wrap" v-if="reportStore.reportContent.dimensions">
              <div class="radar-label">四维度匹配</div>
              <div ref="reportRadarRef" class="report-radar-chart"></div>
              <div class="dim-mini-list">
                <div class="dim-mini" v-for="(dim, idx) in dimensionsList" :key="`dim-${idx}`">
                  <span class="dim-mini-name">{{ dim.name }}</span>
                  <div class="dim-mini-bar">
                    <div class="dim-mini-fill"
                      :style="{ width: dim.score + '%', background: dim.score >= 80 ? '#52c41a' : dim.score >= 60 ? '#667eea' : '#fa8c16' }">
                    </div>
                  </div>
                  <span class="dim-mini-score"
                    :style="{ color: dim.score >= 80 ? '#389e0d' : dim.score >= 60 ? '#667eea' : '#d46b08' }">
                    {{ dim.score }}
                  </span>
                  <div class="dim-detail-text" v-if="dim.detail">{{ dim.detail }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="action-plan-card card" v-if="editedActionPlan.length || isEditing">
          <div class="section-header">
            <h3>行动计划</h3>
            <button v-if="isEditing" class="add-btn" @click="addActionPhase">+ 添加阶段</button>
          </div>
          <div class="timeline">
            <div class="timeline-item" v-for="(phase, idx) in editedActionPlan" :key="`phase-${idx}`">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div class="phase-header" v-if="!isEditing">
                  <span class="phase-title">{{ phase.phase }}</span>
                  <span class="phase-timeline">{{ phase.timeline }}</span>
                </div>
                <div class="phase-edit" v-else>
                  <input v-model="phase.phase" placeholder="阶段名称" class="phase-input" />
                  <input v-model="phase.timeline" placeholder="时间线" class="timeline-input" />
                  <button class="remove-btn" @click="removeActionPhase(idx)">✕</button>
                </div>
                <ul class="phase-goals" v-if="!isEditing">
                  <li v-for="(goal, gIdx) in phase.goals" :key="`goal-${idx}-${gIdx}`">{{ goal }}</li>
                </ul>
                <div class="milestone-check" v-if="!isEditing && phase.milestone_check">
                  <div class="milestone-header">
                    <span class="milestone-icon">🎯</span>
                    <span class="milestone-date">评估节点：{{ phase.milestone_check.date }}</span>
                  </div>
                  <div class="milestone-metric">达标指标：{{ phase.milestone_check.metric }}</div>
                  <div class="milestone-trigger">调整触发：{{ phase.milestone_check.trigger }}</div>
                </div>
                <div class="goals-edit" v-else>
                  <div class="goal-item" v-for="(_goal, gIdx) in phase.goals" :key="`goal-edit-${idx}-${gIdx}`">
                    <input v-model="phase.goals[gIdx]" placeholder="目标内容" class="goal-input" />
                    <button class="remove-goal-btn" @click="removeGoal(idx, gIdx)">✕</button>
                  </div>
                  <button class="add-goal-btn" @click="addGoal(idx)">+ 添加目标</button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="!editedActionPlan.length && !isEditing" class="empty-hint">暂无行动计划</div>
        </div>

        <div class="skill-gaps-card card" v-if="editedSkillGaps.length || isEditing">
          <div class="section-header">
            <h3>技能差距分析</h3>
            <button v-if="isEditing" class="add-btn" @click="addSkillGap">+ 添加技能</button>
          </div>
          <div class="gap-list">
            <div class="gap-item" v-for="(gap, index) in editedSkillGaps" :key="index">
              <div class="gap-header" v-if="!isEditing">
                <span class="gap-skill">{{ gap.skill }}</span>
                <span :class="['gap-badge', gap.importance === 'must_have' ? 'must' : 'nice']">
                  {{ gap.importance === 'must_have' ? '必须' : '加分' }}
                </span>
              </div>
              <div class="gap-edit" v-else>
                <input v-model="gap.skill" placeholder="技能名称" class="skill-input" />
                <select v-model="gap.importance" class="importance-select">
                  <option value="must_have">必须</option>
                  <option value="nice_to_have">加分</option>
                </select>
                <button class="remove-btn" @click="removeSkillGap(index)">✕</button>
              </div>
              <div class="gap-suggestion" v-if="!isEditing && gap.suggestion">{{ gap.suggestion }}</div>
              <textarea v-else-if="isEditing" v-model="gap.suggestion" placeholder="补齐建议" class="suggestion-textarea" />
              <div class="gap-source" v-if="!isEditing && gap.jd_source">
                <span class="source-label">JD来源：</span>
                <span class="source-text">{{ gap.jd_source }}</span>
              </div>
            </div>
          </div>
          <div v-if="!editedSkillGaps.length && !isEditing" class="empty-hint">暂无技能差距分析</div>
        </div>

        <div class="career-path-card card" v-if="editedCareerPath.length || isEditing">
          <div class="section-header">
            <h3>职业发展路径</h3>
            <button v-if="isEditing" class="add-btn" @click="addCareerStep">+ 添加阶段</button>
          </div>
          <div class="path-list">
            <div class="path-item" v-for="(step, index) in editedCareerPath" :key="index">
              <div class="path-index">{{ index + 1 }}</div>
              <div class="path-content">
                <div class="path-title" v-if="!isEditing">{{ step.title || step.job || step }}</div>
                <input v-else v-model="step.title" placeholder="岗位名称" class="path-input" />
                <div class="path-desc" v-if="!isEditing && step.description">{{ step.description }}</div>
                <textarea v-else-if="isEditing" v-model="step.description" placeholder="描述" class="path-desc-input" />
                <button v-if="isEditing" class="remove-btn path-remove" @click="removeCareerStep(index)">✕</button>
              </div>
            </div>
          </div>
          <div v-if="!editedCareerPath.length && !isEditing" class="empty-hint">暂无职业发展路径</div>
        </div>

        <div class="chapters-section" v-if="reportStore.reportContent?.chaptersJson?.length">
          <div class="section-header-title">
            <h3>完整报告内容</h3>
            <span class="chapter-count">共 {{ reportStore.reportContent.chaptersJson.length }} 章</span>
            <span v-if="optimizedChapterTitles.size > 0" class="optimized-summary-badge">
              ✨ {{ optimizedChapterTitles.size }} 个章节已优化
            </span>
          </div>
          <div
            class="chapter-card card"
            :class="{ 'chapter-optimized': optimizedChapterTitles.has(ch.title) }"
            :ref="el => { if (optimizedChapterTitles.has(ch.title) && el && !firstOptimizedRef) firstOptimizedRef = el as HTMLElement }"
            v-for="ch in normalChapters"
            :key="ch.title"
          >
            <div class="chapter-header">
              <span class="chapter-icon">{{ ch.icon }}</span>
              <span class="chapter-title">{{ ch.title }}</span>
              <span
                v-if="getChapterSource(ch.title)"
                :class="['chapter-source-tag', 'source-' + (getChapterSource(ch.title)?.type || '')]"
              >{{ getChapterSource(ch.title)?.label }}</span>
              <span v-if="optimizedChapterTitles.has(ch.title)" class="chapter-optimized-badge">✨ AI已优化</span>
            </div>
            <div class="chapter-body" v-html="renderMd(ch.content)"></div>
            <div class="chapter-items" v-if="ch.action_items?.length">
              <div class="chapter-item" v-for="(item, i) in ch.action_items" :key="i">
                <span class="item-tag">{{ item.timeline || '' }}</span>
                <span class="item-text">{{ item.title || item }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 报告质量反馈区块暂时隐藏（v-if="false"） -->
        <div v-if="false" class="report-eval-section card">
          <div class="eval-header">
            <span class="eval-icon">💬</span>
            <div>
              <div class="eval-title">报告质量反馈</div>
              <div class="eval-subtitle">您的反馈将帮助 AI 针对性优化报告内容</div>
            </div>
          </div>
          <div class="eval-body">
            <div class="eval-row">
              <span class="eval-label">整体评分</span>
              <div class="star-rating">
                <button v-for="n in 5" :key="n" class="star-btn"
                  :class="{ 'star-active': n <= feedbackRating }"
                  @click="feedbackRating = n">★</button>
                <span class="star-label">{{ starLabels[feedbackRating - 1] || '点击评分' }}</span>
              </div>
            </div>
            <div class="eval-row">
              <span class="eval-label">具体问题</span>
              <div class="issue-tags">
                <label v-for="issue in issueOptions" :key="issue" class="issue-tag"
                  :class="{ 'issue-tag-active': feedbackIssues.includes(issue) }">
                  <input type="checkbox" :value="issue" v-model="feedbackIssues" />
                  {{ issue }}
                </label>
              </div>
            </div>
            <div class="eval-row" v-if="normalChapters.length">
              <span class="eval-label">优化章节</span>
              <div class="eval-chapters">
                <label v-for="ch in normalChapters" :key="ch.title" class="eval-ch-chip"
                  :class="{ 'eval-ch-active': feedbackChapters.includes(ch.title) }">
                  <input type="checkbox" :value="ch.title" v-model="feedbackChapters" />
                  <span>{{ ch.icon }}</span> {{ ch.title }}
                </label>
              </div>
            </div>
          </div>
          <div class="eval-footer">
            <button class="eval-submit-btn" :disabled="!feedbackRating || feedbackSubmitting"
              @click="submitFeedbackOptimize">
              {{ feedbackSubmitting ? 'AI 优化中...' : '✨ 提交并优化报告' }}
            </button>
            <button class="eval-skip-btn" @click="feedbackDone = true">跳过</button>
          </div>
        </div>
        <div v-if="false" class="report-eval-section card eval-progress-card">
          <div class="eval-progress-inner">
            <div class="eval-progress-icon">🤖</div>
            <div class="eval-progress-text">AI 正在根据您的反馈优化报告...</div>
          </div>
        </div>
        <div v-if="false" class="report-eval-section card eval-done-card">
          <div class="eval-done-inner">
            <span class="eval-done-icon">✅</span>
            <span class="eval-done-text">感谢您的反馈！</span>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-icon">📄</div>
      <h3>请先上传简历</h3>
      <p>上传简历后才能生成职业报告</p>
      <button class="primary-btn" @click="$router.push('/upload')">
        上传简历
      </button>
    </div>
  </div>

  <!-- 智能润色浮窗 -->
  <Transition name="modal-fade">
    <div class="pm-overlay" v-if="showPolishModal" @click.self="showPolishModal = false">
      <Transition name="modal-slide">
        <div class="pm-dialog" v-if="showPolishModal">
          <!-- 顶部渐变 banner -->
          <div class="pm-header">
            <div class="pm-header-left">
              <span class="pm-header-icon">✨</span>
              <div>
                <div class="pm-title">智能润色</div>
                <div class="pm-subtitle">AI 将重写选中章节，使表达更专业流畅</div>
              </div>
            </div>
            <button class="pm-close" @click="showPolishModal = false">✕</button>
          </div>

          <div class="pm-body">
            <!-- 章节选择 -->
            <div class="pm-section">
              <div class="pm-section-label">
                选择润色章节
                <span class="pm-section-tip">不选则全文润色</span>
              </div>
              <div class="pm-chapters">
                <label
                  v-for="ch in (reportStore.reportContent?.chaptersJson || [])"
                  :key="ch.title"
                  class="pm-chip"
                  :class="{ 'pm-chip-active': polishChapters.includes(ch.title) }"
                >
                  <input type="checkbox" :value="ch.title" v-model="polishChapters" />
                  <span class="pm-chip-icon">{{ ch.icon }}</span>
                  <span class="pm-chip-text">{{ ch.title }}</span>
                  <span class="pm-chip-check" v-if="polishChapters.includes(ch.title)">✓</span>
                </label>
              </div>
            </div>

            <!-- 润色提示 -->
            <div class="pm-section">
              <div class="pm-section-label">
                润色方向
                <span class="pm-section-tip">可选，引导 AI 侧重点</span>
              </div>
              <div class="pm-input-wrap">
                <span class="pm-input-icon">💬</span>
                <input
                  v-model="polishFeedbackHint"
                  class="pm-input"
                  placeholder="例如：突出量化指标、语言更简洁有力..."
                  maxlength="100"
                />
                <span class="pm-char-count">{{ polishFeedbackHint.length }}/100</span>
              </div>
            </div>

            <!-- 说明提示 -->
            <div class="pm-tip-box">
              <span class="pm-tip-icon">💡</span>
              <span>润色完成后可通过「撤销润色」一键还原原始内容</span>
            </div>
          </div>

          <div class="pm-footer">
            <button class="pm-cancel" @click="showPolishModal = false">取消</button>
            <button class="pm-confirm" :disabled="polishingChapters" @click="confirmPolish">
              <span v-if="polishingChapters" class="pm-loading-dot"></span>
              {{ polishingChapters ? '润色中...' : '✨ 开始润色' }}
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { useUserStore } from '../stores/useUserStore'
import { useReportStore } from '../stores/useReportStore'
import { useMatchStore } from '../stores/useMatchStore'
import { reportApi } from '../api/report'
import { matchApi } from '../api/match'
import StepProgress from '../components/StepProgress.vue'
import FeedbackWidget from '../components/FeedbackWidget.vue'
import * as echarts from 'echarts'
import { sanitizeHtml } from '../utils/sanitize'

const router = useRouter()
const userStore = useUserStore()
const reportStore = useReportStore()
const matchStore = useMatchStore()

const targetJobName = ref('')
const showJobList = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const isPolishing = ref(false)
const isAdjusting = ref(false)
const showPolishModal = ref(false)
const polishChapters = ref<string[]>([])
const polishFeedbackHint = ref('')
const polishingChapters = ref(false)
const canUndo = ref(false)
const undoing = ref(false)
const exportingPdf = ref(false)
const exportingWord = ref(false)
const completenessResult = ref<{completeness_score: number, is_complete: boolean, issues: any[]} | null>(null)

const editedActionPlan = ref<any[]>([])
const editedSkillGaps = ref<any[]>([])
const editedCareerPath = ref<any[]>([])

// 报告质量反馈
const feedbackRating = ref(0)
// const feedbackHoverRating = ref(0)
const feedbackIssues = ref<string[]>([])
const feedbackComment = ref('')
const feedbackChapters = ref<string[]>([])
const feedbackSubmitting = ref(false)
const feedbackOptimizing = ref(false)
const feedbackDone = ref(false)
const feedbackOptimizedCount = ref(0)
const optimizedChapterTitles = ref<Set<string>>(new Set())
const firstOptimizedRef = ref<HTMLElement | null>(null)

const starLabels = ['差', '一般', '还好', '不错', '很好']
const issueOptions = ['内容不准确', '建议不实用', '路径规划不清晰', '行业洞察太泛', '计划缺少细节']

const allJobList = ref<string[]>([]) // 由 onMounted 从 /api/jobs 加载真实图谱岗位

const completenessWarnings = computed(() => {
  const chapters = reportStore.reportContent?.chaptersJson || []
  const warnChapter = chapters.find((c: any) => c.type === 'completeness_warnings') as any
  return warnChapter?.items || []
})

const normalChapters = computed(() =>
  (reportStore.reportContent?.chaptersJson || []).filter(
    (c: any) => c.type !== 'completeness_warnings' && c.title
  )
)

const filteredJobs = computed(() => {
  if (!targetJobName.value) return allJobList.value.slice(0, 12)
  return allJobList.value.filter(job =>
    job.toLowerCase().includes(targetJobName.value.toLowerCase())
  )
})

const dimensionsList = computed(() => {
  const dims = reportStore.reportContent?.dimensions || {}
  return [
    { name: '基础要求', score: Math.round(dims.basic_requirements?.score || 0), detail: dims.basic_requirements?.detail },
    { name: '职业技能', score: Math.round(dims.professional_skills?.score || 0), detail: dims.professional_skills?.detail },
    { name: '职业素养', score: Math.round(dims.professional_qualities?.score || 0), detail: dims.professional_qualities?.detail },
    { name: '发展潜力', score: Math.round(dims.development_potential?.score || 0), detail: dims.development_potential?.detail },
  ]
})

// ---- ECharts ----
const reportRadarRef = ref<HTMLElement | null>(null)
const gaugeRef = ref<HTMLElement | null>(null)
let reportRadarChart: echarts.ECharts | null = null
let gaugeChart: echarts.ECharts | null = null

function renderReportCharts(content: any) {
  const dims = content.dimensions || {}
  const scores = [
    Math.round(dims.basic_requirements?.score || 0),
    Math.round(dims.professional_skills?.score || 0),
    Math.round(dims.professional_qualities?.score || 0),
    Math.round(dims.development_potential?.score || 0),
  ]

  // 雷达图
  if (reportRadarRef.value) {
    if (!reportRadarChart) reportRadarChart = echarts.init(reportRadarRef.value)
    reportRadarChart.setOption({
      tooltip: { trigger: 'item' },
      radar: {
        indicator: [
          { name: '基础要求', max: 100 },
          { name: '职业技能', max: 100 },
          { name: '职业素养', max: 100 },
          { name: '发展潜力', max: 100 },
        ],
        shape: 'polygon', splitNumber: 5,
        axisName: { color: '#555', fontSize: 12, fontWeight: 500 },
        splitArea: { areaStyle: { color: ['rgba(102,126,234,0.03)','rgba(102,126,234,0.06)','rgba(102,126,234,0.09)','rgba(102,126,234,0.12)','rgba(102,126,234,0.15)'] } },
        axisLine: { lineStyle: { color: '#dde0f0' } },
        splitLine: { lineStyle: { color: '#dde0f0' } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: scores, name: '匹配度',
          areaStyle: { color: 'rgba(102,126,234,0.25)' },
          lineStyle: { color: '#667eea', width: 2.5 },
          itemStyle: { color: '#764ba2' },
          symbol: 'circle', symbolSize: 6,
        }],
      }],
    }, true)
  }

  // 仪表盘
  if (gaugeRef.value) {
    if (!gaugeChart) gaugeChart = echarts.init(gaugeRef.value)
    const overall = content.overallScore || 0
    const color = overall >= 80 ? '#52c41a' : overall >= 60 ? '#667eea' : '#fa8c16'
    gaugeChart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 210, endAngle: -30,
        min: 0, max: 100,
        splitNumber: 5,
        progress: { show: true, width: 14, itemStyle: { color } },
        axisLine: { lineStyle: { width: 14, color: [[1, '#f0f0f0']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}分',
          color, fontSize: 28, fontWeight: 700,
          offsetCenter: [0, '10%'],
        },
        title: { offsetCenter: [0, '40%'], fontSize: 13, color: '#888' },
        data: [{ value: Math.round(overall), name: '综合匹配度' }],
      }],
    }, true)
  }
}

watch(
  () => reportStore.reportContent,
  async (content) => {
    if (!content) return
    editedActionPlan.value = JSON.parse(JSON.stringify(content.actionPlan || []))
    editedSkillGaps.value = JSON.parse(JSON.stringify(content.skillGaps || []))
    editedCareerPath.value = JSON.parse(JSON.stringify(content.careerPath || []))
    // 新报告加载时重置反馈状态
    feedbackRating.value = 0
    feedbackIssues.value = []
    feedbackComment.value = ''
    feedbackChapters.value = []
    feedbackDone.value = false
    feedbackOptimizedCount.value = 0
    optimizedChapterTitles.value = new Set()
    firstOptimizedRef.value = null
    checkCompleteness()
    await nextTick()
    renderReportCharts(content)
  },
  { immediate: true, flush: 'post' },
)

onUnmounted(() => {
  reportRadarChart?.dispose(); reportRadarChart = null
  gaugeChart?.dispose(); gaugeChart = null
  if (handleClickOutside) {
    document.removeEventListener('click', handleClickOutside)
    handleClickOutside = null
  }
})

function confirmCancel() {
  Modal.confirm({
    title: '确认取消',
    content: '确认取消报告生成？已生成的进度将丢失。',
    okText: '确认取消',
    cancelText: '继续生成',
    onOk: () => {
      reportStore.clearReport()
    }
  })
}

function confirmNewReport() {
  Modal.confirm({
    title: '确认生成新报告',
    content: '确认生成新报告？当前报告数据将被清除。',
    okText: '确认生成',
    cancelText: '取消',
    onOk: () => {
      reportStore.clearReport()
    }
  })
}

function selectJob(job: string) {
  targetJobName.value = job
  showJobList.value = false
}

async function generateReport() {
  if (!targetJobName.value) {
    Message.warning('请选择目标岗位')
    return
  }
  
  if (!userStore.studentId) {
    Message.warning('请先上传简历')
    router.push('/upload')
    return
  }
  
  try {
    const taskId = await reportStore.startGenerate(userStore.studentId, targetJobName.value)
    if (!taskId) {
      Message.error('生成失败：未返回任务ID')
      return
    }
    
    const startTime = Date.now()
    const timeout = 120000
    let pollCount = 0

    // 指数退避：前5次2s，5-15次5s，之后10s
    function getNextInterval(): number {
      if (pollCount < 5) return 2000
      if (pollCount < 15) return 5000
      return 10000
    }

    const poll = async () => {
      const elapsed = Date.now() - startTime
      if (elapsed > timeout) {
        reportStore.setError('报告生成超时，请重试')
        Message.error('报告生成超时，请重试')
        return
      }

      try {
        const statusRes = await reportApi.getStatus(taskId)
        pollCount++

        if (statusRes.status === 'completed') {
          await reportStore.loadReport(taskId)
          Message.success('报告生成完成')
          return
        }

        if (statusRes.status === 'failed') {
          reportStore.setError(statusRes.error_msg || '报告生成失败')
          Message.error(statusRes.error_msg || '报告生成失败')
          return
        }

        if (statusRes.progress) {
          reportStore.updateProgress(statusRes.progress, statusRes.message)
        }

        setTimeout(poll, getNextInterval())
      } catch (e: any) {
        pollCount++
        setTimeout(poll, getNextInterval())
      }
    }

    setTimeout(poll, 2000)
  } catch (e: any) {
    Message.error(e?.message || '生成报告失败')
  }
}

async function toggleEditMode() {
  if (isEditing.value) {
    await saveChanges()
  } else {
    isEditing.value = true
  }
}

async function saveChanges() {
  if (!reportStore.reportId) {
    Message.error('报告ID不存在')
    return
  }
  
  saving.value = true
  try {
    await reportApi.update(reportStore.reportId, {
      action_plan: editedActionPlan.value,
      skill_gaps: editedSkillGaps.value,
      career_path: editedCareerPath.value,
    })
    
    reportStore.reportContent = {
      ...(reportStore.reportContent || {}),
      reportId: reportStore.reportContent?.reportId || '',
      studentId: reportStore.reportContent?.studentId || '',
      jobName: reportStore.reportContent?.jobName || '',
      overallScore: reportStore.reportContent?.overallScore || 0,
      dimensions: reportStore.reportContent?.dimensions || {},
      chaptersJson: reportStore.reportContent?.chaptersJson || [],
      createdAt: reportStore.reportContent?.createdAt || '',
      actionPlan: editedActionPlan.value,
      skillGaps: editedSkillGaps.value,
      careerPath: editedCareerPath.value,
    }
    reportStore.saveToStorage()
    Message.success('保存成功')
    isEditing.value = false
  } catch (error: any) {
    Message.error(error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function addActionPhase() {
  editedActionPlan.value.push({
    phase: '',
    timeline: '',
    goals: [''],
  })
}

function removeActionPhase(index: number) {
  editedActionPlan.value.splice(index, 1)
}

function addGoal(phaseIndex: number) {
  editedActionPlan.value[phaseIndex].goals.push('')
}

function removeGoal(phaseIndex: number, goalIndex: number | string) {
  editedActionPlan.value[phaseIndex].goals.splice(Number(goalIndex), 1)
}

function addSkillGap() {
  editedSkillGaps.value.push({
    skill: '',
    importance: 'nice_to_have',
    suggestion: '',
    jd_source: '',
  })
}

function removeSkillGap(index: number) {
  editedSkillGaps.value.splice(index, 1)
}

function addCareerStep() {
  editedCareerPath.value.push({
    title: '',
    description: '',
  })
}

function removeCareerStep(index: number) {
  editedCareerPath.value.splice(index, 1)
}

function exportWord() {
  if (!reportStore.reportId || exportingWord.value) return
  exportingWord.value = true
  const link = document.createElement('a')
  link.href = `/api/report/${reportStore.reportId}/word`
  link.download = `职业规划报告_${reportStore.reportContent?.jobName || '未命名'}.docx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  Message.success('Word文档下载已开始')
  setTimeout(() => { exportingWord.value = false }, 2000)
}

function exportPdf() {
  if (!reportStore.reportId || exportingPdf.value) return
  exportingPdf.value = true
  const link = document.createElement('a')
  link.href = `/api/report/${reportStore.reportId}/pdf`
  link.download = `职业规划报告_${reportStore.reportContent?.jobName || '未命名'}.pdf`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  Message.success('PDF下载已开始')
  setTimeout(() => { exportingPdf.value = false }, 2000)
}

async function checkCompleteness() {
  if (!reportStore.reportId) return
  try {
    completenessResult.value = await reportApi.getCompleteness(reportStore.reportId)
  } catch {
    // 静默失败，不影响主流程
  }
}

function handleLowRating() {
  if (!reportStore.reportId || isAdjusting.value) return
  Modal.confirm({
    title: '报告质量反馈',
    content: 'AI 检测到您对报告不满意，是否希望系统自动优化报告内容？（将重新润色核心章节）',
    okText: '立即优化',
    cancelText: '暂不优化',
    onOk: async () => {
      isAdjusting.value = true
      try {
        const result = await reportApi.adjust(reportStore.reportId!, {
          feedback_summary: '用户反馈报告内容不满意，请优化语言质量和建议具体性',
        })
        if (result.adjusted) {
          // 重新加载报告以获取更新后的章节
          await reportStore.loadReport(reportStore.reportId!)
          Message.success(`已优化 ${result.chapters_count} 个章节`)
        } else {
          Message.info('报告已是最新状态')
        }
      } catch (e: any) {
        Message.error(e?.message || '优化失败，请稍后重试')
      } finally {
        isAdjusting.value = false
      }
    },
  })
}

async function submitFeedbackOptimize() {
  if (!reportStore.reportId || !feedbackRating.value) return
  feedbackSubmitting.value = true
  feedbackOptimizing.value = true
  try {
    const result = await reportApi.feedbackOptimize(reportStore.reportId, {
      rating: feedbackRating.value,
      issues: feedbackIssues.value,
      comment: feedbackComment.value,
      chapters: feedbackChapters.value.length > 0 ? feedbackChapters.value : null,
    })
    if (result.optimized && result.chapters_json) {
      if (reportStore.reportContent) {
        reportStore.reportContent.chaptersJson = result.chapters_json
        reportStore.saveToStorage()
      }
      feedbackOptimizedCount.value = result.chapters_count
      // 记录被优化的章节，用于高亮展示
      const optimized = feedbackChapters.value.length > 0
        ? feedbackChapters.value
        : normalChapters.value.map(ch => ch.title)
      firstOptimizedRef.value = null  // 重置，让 :ref 绑定捕获到第一个优化章节
      optimizedChapterTitles.value = new Set(optimized)
      // 等 DOM 更新后滚动到第一个优化章节
      await nextTick()
      await nextTick()  // 双 tick 确保 :ref 回调完成
      const scrollTarget = firstOptimizedRef.value as HTMLElement | null
      if (scrollTarget) {
        scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
      // 10分钟后自动清除高亮
      setTimeout(() => { optimizedChapterTitles.value = new Set() }, 10 * 60 * 1000)
    }
    feedbackDone.value = true
    Message.success(`AI 已优化 ${result.chapters_count} 个章节`)
  } catch (e: any) {
    Message.error(e?.message || '优化失败，请稍后重试')
  } finally {
    feedbackSubmitting.value = false
    feedbackOptimizing.value = false
  }
}

async function polishReport() {
  showPolishModal.value = true
}

async function confirmPolish() {
  if (!reportStore.reportId) return
  polishingChapters.value = true
  showPolishModal.value = false
  try {
    const result = await reportApi.polish(reportStore.reportId, {
      chapter_titles: polishChapters.value,
      feedback_hint: polishFeedbackHint.value,
    })
    if (reportStore.reportContent) {
      if (result.chapters_json) reportStore.reportContent.chaptersJson = result.chapters_json
      if (result.action_plan)   reportStore.reportContent.actionPlan  = result.action_plan
      if (result.skill_gaps)    reportStore.reportContent.skillGaps   = result.skill_gaps
    }
    canUndo.value = !!result.snapshot_hash
    Message.success('报告润色完成')
  } catch (e: any) {
    Message.error(e.message || '润色失败')
  } finally {
    polishingChapters.value = false
    polishChapters.value = []
    polishFeedbackHint.value = ''
  }
}

async function undoPolish() {
  if (!reportStore.reportId) return
  undoing.value = true
  try {
    await reportApi.undoPolish(reportStore.reportId)
    // 重新加载报告以获取还原后内容
    await reportStore.loadReport(reportStore.reportId)
    canUndo.value = false
    Message.success('已撤销润色')
  } catch (e: any) {
    Message.error(e.message || '撤销失败')
  } finally {
    undoing.value = false
  }
}

const CHAPTER_SOURCE_MAP: Record<string, { label: string; type: string }> = {
  '综合评估': { label: '规则计算', type: 'rule' },
  '个人概述': { label: '规则计算', type: 'rule' },
  '人岗匹配分析': { label: '市场数据', type: 'market' },
  '技能差距分析': { label: '市场数据', type: 'market' },
  '职业路径规划': { label: '图谱数据', type: 'data' },
  '职业发展路径': { label: '图谱数据', type: 'data' },
  '行业洞察': { label: '真实JD', type: 'market' },
  '行动计划': { label: 'AI辅助', type: 'ai' },
  '短期计划': { label: 'AI辅助', type: 'ai' },
  '中期规划': { label: 'AI辅助', type: 'ai' },
}

function getChapterSource(title: string) {
  if (!title) return null
  for (const key of Object.keys(CHAPTER_SOURCE_MAP)) {
    if (title.includes(key)) return CHAPTER_SOURCE_MAP[key]
  }
  return null
}

function renderMd(text: string): string {
  if (!text) return ''

  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  const fmt = (s: string) => s
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')

  const lines = escaped.split('\n')
  const out: string[] = []
  let inUl = false
  let inTable = false
  let tableIsHeader = true
  let paraLines: string[] = []

  const flushPara = () => {
    if (paraLines.length) {
      const content = paraLines.join(' ').trim()
      if (content) out.push(`<p>${content}</p>`)
      paraLines = []
    }
  }
  const flushUl = () => { if (inUl) { out.push('</ul>'); inUl = false } }
  const flushTable = () => { if (inTable) { out.push('</tbody></table>'); inTable = false; tableIsHeader = true } }

  for (const raw of lines) {
    // Skip bare placeholder lines like "####" / "### " with no real content
    if (/^#{2,}\s*$/.test(raw)) continue

    // Markdown table row
    if (/^\|.+\|$/.test(raw.trim())) {
      flushPara(); flushUl()
      // Separator row (---|---) → marks previous row as header
      if (/^[\s|:=-]+$/.test(raw.trim())) continue
      const cells = raw.trim().split('|')
        .filter((_, i, a) => i > 0 && i < a.length - 1)
        .map(c => fmt(c.trim()))
      if (!inTable) {
        out.push('<table><thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>')
        inTable = true
        tableIsHeader = false
      } else if (tableIsHeader) {
        out.push('<tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr>')
      } else {
        out.push('<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>')
      }
      continue
    }

    if (inTable) flushTable()

    const line = fmt(raw)

    if (/^#### (.+)$/.test(raw)) {
      flushPara(); flushUl()
      out.push(`<h5>${fmt(raw.replace(/^#### /, ''))}</h5>`)
    } else if (/^### (.+)$/.test(raw)) {
      flushPara(); flushUl()
      out.push(`<h4>${fmt(raw.replace(/^### /, ''))}</h4>`)
    } else if (/^## (.+)$/.test(raw)) {
      flushPara(); flushUl()
      out.push(`<h3>${fmt(raw.replace(/^## /, ''))}</h3>`)
    } else if (/^# (.+)$/.test(raw)) {
      flushPara(); flushUl()
      out.push(`<h2>${fmt(raw.replace(/^# /, ''))}</h2>`)
    } else if (/^&gt; (.+)$/.test(line)) {
      flushPara(); flushUl()
      out.push(`<blockquote>${line.replace(/^&gt; /, '')}</blockquote>`)
    } else if (/^[-*] (.+)$/.test(raw)) {
      flushPara()
      if (!inUl) { out.push('<ul>'); inUl = true }
      out.push(`<li>${fmt(raw.replace(/^[-*] /, ''))}</li>`)
    } else if (raw.trim() === '') {
      flushPara(); flushUl()
    } else {
      flushUl()
      paraLines.push(line)
    }
  }
  flushPara(); flushUl(); flushTable()

  return sanitizeHtml(out.join('\n'))
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

let handleClickOutside: ((e: MouseEvent) => void) | null = null

onMounted(async () => {
  handleClickOutside = (e: MouseEvent) => {
    const target = e.target as HTMLElement
    if (!target.closest('.job-select')) {
      showJobList.value = false
    }
  }
  document.addEventListener('click', handleClickOutside)
  
  matchApi.getJobs().then(jobs => {
    if (jobs && jobs.length > 0) allJobList.value = jobs
  }).catch(() => {})

  if (matchStore.currentJob) {
    targetJobName.value = matchStore.currentJob
  }

  // 修复：status='done' 但 reportContent 丢失（刷新后localStorage状态残留）
  if (reportStore.status === 'done' && !reportStore.reportContent && reportStore.reportId) {
    try {
      await reportStore.loadReport(reportStore.reportId)
    } catch {
      reportStore.clearReport()
    }
  }

  // 修复：status='generating'/'pending' 但已无活跃任务（服务器重启后DB记录停滞）
  if ((reportStore.status === 'generating' || reportStore.status === 'pending') && reportStore.reportId) {
    try {
      const statusRes = await reportApi.getStatus(reportStore.reportId)
      if (statusRes.status === 'failed') {
        reportStore.clearReport()
      }
    } catch {
      // 网络异常时不重置，等轮询自然超时
    }
  }

  const pendingReportId = localStorage.getItem('pending_report_id')
  if (pendingReportId && reportStore.status === 'idle') {
    try {
      await reportStore.loadReport(pendingReportId)
    } catch (e) {
      localStorage.removeItem('pending_report_id')
    }
  }
})

onUnmounted(() => {
  if (reportStore.status === 'generating' && reportStore.reportId) {
    localStorage.setItem('pending_report_id', reportStore.reportId)
  }
})
</script>

<style scoped>
.report-page {
  min-height: 100vh;
  background: #f8fafc;
}
.empty-state-page {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 80px 24px; text-align: center;
}
.empty-state-icon { font-size: 64px; margin-bottom: 16px; }
.empty-state-page h2 { font-size: 20px; color: #1d2129; margin: 0 0 8px; }
.empty-state-page p { color: #86909c; margin: 0 0 24px; }
/* O4-b: 移动端报告页适配 */
@media (max-width: 768px) {
  .report-container { padding: 12px; }
  .chapters-grid { grid-template-columns: 1fr !important; }
  .action-bar { position: fixed; bottom: 0; left: 0; right: 0;
    padding: 12px 16px; background: #fff; box-shadow: 0 -2px 8px rgba(0,0,0,.08);
    display: flex; gap: 8px; }
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 32px;
  background: white;
  border-bottom: 1px solid #eee;
}

.back-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid #eee;
  background: #fff;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #f5f5f5;
}

.header-content h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.header-content p {
  font-size: 14px;
  color: #666;
  margin: 4px 0 0;
}

.report-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 16px;
  color: #1a1a2e;
}

.generate-section .card {
  text-align: center;
}

.hint {
  color: #666;
  font-size: 14px;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.job-select {
  position: relative;
}

.job-select input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}

.job-select input:focus {
  border-color: #667eea;
}

.job-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  margin-top: 4px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
}

.job-option {
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.job-option:hover {
  background: #f5f5f5;
}

.primary-btn {
  width: 100%;
  padding: 14px 24px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.progress-section .card {
  text-align: center;
}

.progress-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 15px;
  color: #333;
  margin-bottom: 8px;
}

.progress-hint {
  font-size: 13px;
  color: #999;
}

/* ====== 智能润色浮窗 ====== */
.modal-fade-enter-active,
.modal-fade-leave-active { transition: opacity 0.22s ease; }
.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; }

.modal-slide-enter-active { transition: transform 0.26s cubic-bezier(0.34, 1.26, 0.64, 1), opacity 0.22s ease; }
.modal-slide-leave-active { transition: transform 0.2s ease, opacity 0.18s ease; }
.modal-slide-enter-from { transform: translateY(-24px) scale(0.97); opacity: 0; }
.modal-slide-leave-to  { transform: translateY(12px) scale(0.97); opacity: 0; }

.pm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 10, 30, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 20px;
}

.pm-dialog {
  background: #fff;
  border-radius: 18px;
  width: 520px;
  max-width: 95vw;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px rgba(80, 40, 160, 0.22), 0 4px 16px rgba(0,0,0,0.12);
}

.pm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 18px;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: #fff;
  flex-shrink: 0;
}

.pm-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pm-header-icon {
  font-size: 26px;
  line-height: 1;
  filter: drop-shadow(0 1px 3px rgba(255,255,255,0.3));
}

.pm-title {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.2;
}

.pm-subtitle {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 2px;
}

.pm-close {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: rgba(255,255,255,0.2);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
  flex-shrink: 0;
}
.pm-close:hover { background: rgba(255,255,255,0.35); }

.pm-body {
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.pm-section { display: flex; flex-direction: column; gap: 10px; }

.pm-section-label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.pm-section-tip {
  font-size: 12px;
  font-weight: 400;
  color: #aaa;
}

.pm-chapters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pm-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 13px;
  border-radius: 20px;
  border: 1.5px solid #e0d7f7;
  background: #faf8ff;
  color: #555;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s;
  user-select: none;
}
.pm-chip input { display: none; }
.pm-chip:hover { border-color: #a855f7; color: #7c3aed; background: #f5f0ff; }

.pm-chip-active {
  border-color: #7c3aed;
  background: linear-gradient(135deg, #f0ebff 0%, #ede9fe 100%);
  color: #5b21b6;
  font-weight: 600;
}

.pm-chip-icon { font-size: 14px; }
.pm-chip-text { }
.pm-chip-check { font-size: 11px; color: #7c3aed; font-weight: 700; }

.pm-input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
  transition: border-color 0.18s;
}
.pm-input-wrap:focus-within { border-color: #a855f7; background: #fff; }

.pm-input-icon { font-size: 15px; flex-shrink: 0; }

.pm-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 11px 0;
  font-size: 14px;
  color: #333;
  outline: none;
}
.pm-input::placeholder { color: #bbb; }

.pm-char-count {
  font-size: 11px;
  color: #ccc;
  flex-shrink: 0;
}

.pm-tip-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 11px 14px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 10px;
  font-size: 12.5px;
  color: #8c6d00;
}
.pm-tip-icon { flex-shrink: 0; }

.pm-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.pm-cancel {
  padding: 9px 20px;
  border-radius: 9px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}
.pm-cancel:hover { border-color: #bbb; color: #333; }

.pm-confirm {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 10px 26px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 3px 10px rgba(124, 58, 237, 0.3);
}
.pm-confirm:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 5px 16px rgba(124, 58, 237, 0.45);
}
.pm-confirm:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

@keyframes pm-spin { to { transform: rotate(360deg); } }
.pm-loading-dot {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: pm-spin 0.7s linear infinite;
  flex-shrink: 0;
}
/* ====== 智能润色浮窗 end ====== */

.cancel-btn {
  margin-top: 16px;
  padding: 8px 24px;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 8px;
  color: #666;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.cancel-btn:hover {
  border-color: #999;
  color: #333;
}

.error-section .card {
  text-align: center;
}

.error-card .error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-card h3 {
  margin-bottom: 8px;
}

.error-card p {
  color: #666;
  margin-bottom: 20px;
}

/* ====== 报告标题栏 ====== */
.report-title-strip {
  padding: 16px 24px;
  margin-bottom: 12px;
}

.report-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.report-title-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.report-title-left h2 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: #1a1a2e;
}

.report-badge {
  padding: 4px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}

.completeness-score-tag {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.score-ok { background: #f0fff4; color: #389e0d; border: 1px solid #b7eb8f; }
.score-warn { background: #fffbe6; color: #d46b08; border: 1px solid #ffe58f; }

.report-title-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.ai-disclaimer-inline {
  font-size: 11px;
  color: #aaa;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 6px;
}

.report-date {
  font-size: 12px;
  color: #bbb;
}

/* ====== 警告条 ====== */
.alert-strip {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.alert-item {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.alert-warn {
  background: #fff7e6;
  border: 1px solid #ffd591;
  color: #d46b08;
}

.alert-info {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #0958d9;
}

/* ====== 操作工具栏 ====== */
.report-toolbar {
  padding: 14px 20px;
  margin-bottom: 20px;
}

.toolbar-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-right {
  margin-left: auto;
}

.action-btn.polish-btn {
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);
}

.action-btn.polish-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4);
}

.action-btn.polish-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.action-btn.undo-btn {
  background: #fff7e6;
  color: #d46b08;
  border-color: #ffd591;
}

.action-btn.undo-btn:hover:not(:disabled) {
  background: #fff1d6;
  border-color: #fa8c16;
}

.action-btn.undo-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-btn {
  padding: 10px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  background: white;
  color: #667eea;
  border: 1px solid #667eea;
}

.action-btn:hover {
  background: #f0f4ff;
}

.action-btn.active {
  background: #667eea;
  color: white;
}

.action-btn.danger-btn {
  border-color: #ff4d4f;
  color: #ff4d4f;
}

.action-btn.danger-btn:hover {
  background: #fff1f0;
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.action-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
}

.score-overview {
  padding-bottom: 8px;
}

.overview-charts {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 24px;
  align-items: start;
}

.gauge-wrap { display: flex; flex-direction: column; align-items: center; }
.gauge-chart { width: 200px; height: 160px; }

.radar-wrap { display: flex; flex-direction: column; gap: 8px; }
.radar-label { font-size: 13px; color: #888; font-weight: 500; }
.report-radar-chart { width: 100%; height: 200px; }

.dim-mini-list { display: flex; flex-direction: column; gap: 8px; margin-top: 4px; }
.dim-mini {
  display: grid;
  grid-template-columns: 60px 1fr 32px;
  align-items: center;
  gap: 8px;
}
.dim-mini-name { font-size: 12px; color: #555; }
.dim-mini-bar { height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
.dim-mini-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.dim-mini-score { font-size: 12px; font-weight: 700; text-align: right; }
.dim-detail-text {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
  line-height: 1.4;
  grid-column: 1 / -1;
  padding: 4px 8px;
  background: #f8fafc;
  border-radius: 4px;
}

@media (max-width: 640px) {
  .overview-charts { grid-template-columns: 1fr; }
  .gauge-chart { width: 100%; }
}

.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dimension-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dim-header {
  display: flex;
  justify-content: space-between;
}

.dim-name {
  font-size: 14px;
  font-weight: 500;
}

.dim-score {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}

.dim-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.dim-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.dim-desc {
  font-size: 12px;
  color: #999;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
}

.add-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  background: #f0f4ff;
  color: #667eea;
  border: 1px solid #667eea;
  transition: all 0.2s;
}

.add-btn:hover {
  background: #667eea;
  color: white;
}

.timeline {
  position: relative;
  padding-left: 28px;
}

.timeline-item {
  position: relative;
  padding-bottom: 28px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -28px;
  top: 4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -22px;
  top: 18px;
  width: 2px;
  height: calc(100% - 14px);
  background: linear-gradient(180deg, #667eea 0%, #e5e5e5 100%);
}

.timeline-item:last-child::before {
  display: none;
}

.phase-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.phase-title {
  font-weight: 600;
  font-size: 15px;
  color: #1a1a2e;
}

.phase-timeline {
  font-size: 13px;
  color: #667eea;
}

.phase-goals {
  margin: 0;
  padding-left: 20px;
}

.phase-goals li {
  font-size: 14px;
  color: #666;
  margin: 4px 0;
}

.milestone-check {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f0f7ff;
  border-left: 3px solid #4096ff;
  border-radius: 0 6px 6px 0;
  font-size: 13px;
}

.milestone-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #1677ff;
  margin-bottom: 4px;
}

.milestone-icon {
  font-size: 14px;
}

.milestone-metric,
.milestone-trigger {
  color: #555;
  margin-top: 3px;
  line-height: 1.5;
}

.milestone-trigger {
  color: #888;
  font-style: italic;
}

.phase-edit {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.phase-input {
  flex: 1;
  min-width: 150px;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
}

.timeline-input {
  width: 120px;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
}

.remove-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid #ff4d4f;
  background: white;
  color: #ff4d4f;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #ff4d4f;
  color: white;
}

.goals-edit {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.goal-item {
  display: flex;
  gap: 8px;
}

.goal-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
}

.remove-goal-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid #ddd;
  background: white;
  color: #999;
  cursor: pointer;
  font-size: 12px;
}

.remove-goal-btn:hover {
  border-color: #ff4d4f;
  color: #ff4d4f;
}

.add-goal-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  background: #f5f5f5;
  color: #666;
  border: 1px solid #e5e5e5;
  align-self: flex-start;
}

.gap-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.gap-item {
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid #f0f0f0;
  border-left: 4px solid #667eea;
  transition: box-shadow 0.2s, transform 0.2s;
}

.gap-item:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
  transform: translateX(2px);
}

.gap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.gap-skill {
  font-weight: 500;
  font-size: 15px;
}

.gap-badge {
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.gap-badge.must {
  background: #fff1f0;
  color: #f5222d;
}

.gap-badge.nice {
  background: #fff7e6;
  color: #fa8c16;
}

.gap-edit {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.skill-input {
  flex: 1;
  min-width: 150px;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
}

.importance-select {
  width: 100px;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
}

.gap-suggestion {
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
}

.suggestion-textarea {
  width: 100%;
  min-height: 60px;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
}

.gap-source {
  font-size: 12px;
  color: #999;
}

.source-label {
  color: #666;
}

.path-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.path-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid #f0f0f0;
  transition: box-shadow 0.2s, transform 0.2s;
}

.path-item:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
  transform: translateX(2px);
}

.path-index {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.path-content {
  flex: 1;
}

.path-title {
  font-weight: 600;
  font-size: 15px;
}

.path-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 8px;
}

.path-desc {
  font-size: 14px;
  color: #666;
  margin-top: 6px;
  line-height: 1.5;
}

.path-desc-input {
  width: 100%;
  min-height: 50px;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
}

.path-remove {
  margin-top: 4px;
}

.empty-hint {
  text-align: center;
  color: #999;
  font-size: 14px;
  padding: 24px 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #e5e5e5;
}

.empty-hint::before {
  content: '📋 ';
  opacity: 0.6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1a1a2e;
}

.empty-state p {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
}

.empty-state .primary-btn {
  width: auto;
  padding: 12px 32px;
}

.chapters-section {
  margin-top: 4px;
}

.section-header-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-header-title h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.chapter-count {
  font-size: 13px;
  color: #999;
  padding: 2px 10px;
  background: #f5f5f5;
  border-radius: 20px;
}

.chapter-card {
  padding: 20px 24px;
}

.chapter-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.chapter-icon {
  font-size: 18px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f4ff;
  border-radius: 8px;
  flex-shrink: 0;
}

.chapter-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
}

.chapter-body {
  font-size: 14px;
  color: #444;
  line-height: 1.75;
}

.chapter-body :deep(h2) {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 20px 0 8px;
  padding: 6px 12px;
  background: #f0f4ff;
  border-left: 3px solid #667eea;
  border-radius: 0 6px 6px 0;
}

.chapter-body :deep(h3) {
  font-size: 14px;
  font-weight: 700;
  color: #2d2d4e;
  margin: 16px 0 6px;
  padding-left: 10px;
  border-left: 3px solid #b3bcf5;
}

.chapter-body :deep(h4) {
  font-size: 13px;
  font-weight: 600;
  color: #444;
  margin: 12px 0 4px;
  padding-left: 8px;
  border-left: 2px solid #d0d5f0;
}

.chapter-body :deep(h5) {
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  margin: 10px 0 4px;
  display: inline-block;
  background: #f0f4ff;
  padding: 2px 10px;
  border-radius: 4px;
}

.chapter-body :deep(ul),
.chapter-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.chapter-body :deep(li) {
  margin: 5px 0;
  line-height: 1.65;
  color: #444;
}

.chapter-body :deep(li)::marker {
  color: #667eea;
}

.chapter-body :deep(p) {
  margin: 8px 0;
}

.chapter-body :deep(strong) {
  color: #667eea;
  font-weight: 700;
  background: #f0f4ff;
  padding: 0 3px;
  border-radius: 3px;
}

.chapter-body :deep(em) {
  color: #764ba2;
  font-style: normal;
  font-weight: 500;
}

.chapter-body :deep(a) {
  color: #667eea;
  text-decoration: underline;
}

.chapter-body :deep(blockquote) {
  margin: 12px 0;
  padding: 10px 16px;
  background: #f8fafc;
  border-left: 4px solid #667eea;
  color: #555;
  border-radius: 0 8px 8px 0;
}

.chapter-body :deep(code) {
  background: #f0f0f0;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #c0392b;
}

.chapter-body :deep(pre) {
  background: #f8fafc;
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
  border: 1px solid #eee;
}

.chapter-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #333;
}

.chapter-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.chapter-body :deep(th),
.chapter-body :deep(td) {
  border: 1px solid #e5e5e5;
  padding: 8px 12px;
  text-align: left;
}

.chapter-body :deep(th) {
  background: #f5f7ff;
  font-weight: 600;
  color: #333;
}

.chapter-body :deep(tr:nth-child(even)) {
  background: #fafbff;
}

.chapter-items {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
}

.item-tag {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 4px;
  background: #ede9fe;
  color: #764ba2;
  font-size: 12px;
  font-weight: 500;
}

.item-text {
  color: #444;
}

/* 章节来源标签 */
.chapter-source-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 400;
  margin-left: auto;
  flex-shrink: 0;
  opacity: 0.7;
}

.source-rule { background: #f0fafb; color: #08979c; border: 1px solid #d6f0ee; }
.source-ai { background: #faf5ff; color: #7c3aed; border: 1px solid #e9d5ff; }
.source-market { background: #fffbf0; color: #b45309; border: 1px solid #fde68a; }
.source-data { background: #f0f5ff; color: #3b5bdb; border: 1px solid #c5d0fa; }

/* 反馈优化高亮 */
.chapter-optimized {
  border: 1.5px solid #52c41a !important;
  box-shadow: 0 0 0 4px rgba(82, 196, 26, 0.08), 0 4px 16px rgba(82, 196, 26, 0.12) !important;
  animation: optimized-glow 0.7s ease;
}

@keyframes optimized-glow {
  0%   { box-shadow: 0 0 0 0 rgba(82, 196, 26, 0.4); }
  50%  { box-shadow: 0 0 0 10px rgba(82, 196, 26, 0.15); }
  100% { box-shadow: 0 0 0 4px rgba(82, 196, 26, 0.08), 0 4px 16px rgba(82, 196, 26, 0.12); }
}

.chapter-optimized-badge {
  font-size: 11px;
  font-weight: 600;
  color: #389e0d;
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  border: 1px solid #b7eb8f;
  border-radius: 10px;
  padding: 2px 9px;
  flex-shrink: 0;
  white-space: nowrap;
}

.chapter-optimized .chapter-header {
  border-bottom-color: rgba(82, 196, 26, 0.2);
}

.optimized-summary-badge {
  font-size: 12px;
  font-weight: 600;
  color: #389e0d;
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  border: 1px solid #b7eb8f;
  border-radius: 12px;
  padding: 3px 12px;
}

/* ====== 报告质量反馈区块 ====== */
.report-eval-section {
  margin-top: 24px;
  padding: 24px 28px;
  border-radius: 16px;
  background: white;
  border: 1px solid #f0f0f0;
}

.eval-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f5f5f5;
}

.eval-icon {
  font-size: 28px;
  line-height: 1;
  flex-shrink: 0;
}

.eval-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 3px;
}

.eval-subtitle {
  font-size: 13px;
  color: #888;
}

.eval-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.eval-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.eval-label {
  font-size: 13px;
  font-weight: 600;
  color: #444;
}

.eval-optional {
  font-weight: 400;
  color: #aaa;
  font-size: 12px;
}

/* 评星 */
.star-rating {
  display: flex;
  align-items: center;
  gap: 6px;
}

.star-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #ddd;
  transition: color 0.15s, transform 0.1s;
  padding: 0 2px;
  line-height: 1;
}

.star-btn.star-active,
.star-btn.star-hover {
  color: #faad14;
}

.star-btn:hover {
  transform: scale(1.15);
}

.star-label {
  font-size: 13px;
  color: #666;
  margin-left: 6px;
  min-width: 36px;
}

/* 问题标签 */
.issue-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.issue-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  background: white;
  color: #555;
  transition: all 0.2s;
  user-select: none;
}

.issue-tag input {
  display: none;
}

.issue-tag:hover {
  border-color: #667eea;
  color: #667eea;
  background: #f0f4ff;
}

.issue-tag-active {
  border-color: #667eea !important;
  background: #667eea !important;
  color: white !important;
}

/* 章节芯片 */
.eval-chapters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.eval-ch-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  background: white;
  color: #666;
  transition: all 0.2s;
  user-select: none;
}

.eval-ch-chip input {
  display: none;
}

.eval-ch-chip:hover {
  border-color: #764ba2;
  color: #764ba2;
  background: #f9f0ff;
}

.eval-ch-active {
  border-color: #764ba2 !important;
  background: #764ba2 !important;
  color: white !important;
}

/* 文本区域 */
.eval-textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  font-size: 13px;
  resize: vertical;
  outline: none;
  font-family: inherit;
  color: #333;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.eval-textarea:focus {
  border-color: #667eea;
}

.eval-char-count {
  font-size: 12px;
  color: #bbb;
  text-align: right;
}

/* 底部操作栏 */
.eval-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f5f5f5;
}

.eval-submit-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.eval-submit-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.eval-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.eval-loading {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: white;
  border-radius: 50%;
  animation: pm-spin 0.7s linear infinite;
}

.eval-skip-btn {
  padding: 10px 18px;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 10px;
  font-size: 13px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}

.eval-skip-btn:hover {
  border-color: #999;
  color: #555;
}

/* 优化进行中 */
.eval-progress-card {
  text-align: center;
  padding: 32px 24px;
}

.eval-progress-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.eval-progress-icon {
  font-size: 40px;
  animation: eval-bounce 1.4s ease-in-out infinite;
}

@keyframes eval-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.eval-progress-text {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.eval-progress-bar {
  width: 240px;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.eval-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 3px;
  animation: eval-bar 2.5s ease-in-out infinite;
}

@keyframes eval-bar {
  0%   { width: 10%; margin-left: 0; }
  50%  { width: 60%; margin-left: 20%; }
  100% { width: 10%; margin-left: 90%; }
}

.eval-progress-hint {
  font-size: 12px;
  color: #aaa;
}

/* 完成状态 */
.eval-done-card {
  padding: 16px 24px;
}

.eval-done-inner {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eval-done-icon {
  font-size: 20px;
}

.eval-done-text {
  font-size: 14px;
  color: #52c41a;
  font-weight: 500;
}
/* ====== 报告质量反馈区块 end ====== */

/* ====== E-2: 移动端适配 ====== */
@media (max-width: 768px) {
  .report-container {
    padding: 12px;
  }
  .overview-charts {
    grid-template-columns: 1fr !important;
  }
  .report-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .chapter-card {
    padding: 16px;
  }
  .action-plan-grid,
  .gap-grid {
    grid-template-columns: 1fr !important;
  }
  .chapter-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .feedback-row {
    flex-direction: column;
    gap: 8px;
  }
  .export-actions {
    flex-direction: column;
    gap: 8px;
  }
  .export-actions button {
    width: 100%;
  }
}
</style>
