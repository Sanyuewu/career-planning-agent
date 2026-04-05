<template>
  <div class="assessment-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()"><span>←</span></button>
      <div class="header-content">
        <h1>能力测评</h1>
        <p>三维度能力自测 · 结果自动同步至学生画像</p>
      </div>
    </div>

    <!-- 测评前：岗位选择 -->
    <div class="assessment-start" v-if="phase === 'start'">
      <div class="start-card">
        <div class="start-icon">🧪</div>
        <h2>开始能力测评</h2>
        <p>测评包含三个部分：<strong>逻辑推理（5题）</strong>、<strong>职业倾向（10题）</strong>、<strong>技术自评（8题）</strong></p>
        <p class="hint-text">预计用时约 10-15 分钟，测评结果将以 40% 权重合并至你的能力画像</p>
        <div class="job-hint-row">
          <label>你的目标岗位方向：</label>
          <select v-model="jobHint" class="job-select">
            <option value="">请选择</option>
            <option value="后端开发">后端开发</option>
            <option value="前端开发">前端开发</option>
            <option value="数据分析">数据分析</option>
            <option value="算法/AI">算法/AI</option>
            <option value="DevOps">DevOps</option>
          </select>
        </div>
        <button class="start-btn" @click="startAssessment" :disabled="!jobHint || loadingQ">
          {{ loadingQ ? '加载题目中...' : '开始测评' }}
        </button>
      </div>
    </div>

    <!-- 测评中：步骤式答题 -->
    <div class="assessment-quiz" v-if="phase === 'quiz' && currentQuestion">
      <div class="quiz-progress">
        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
        <span class="progress-text">{{ currentIndex + 1 }} / {{ allQuestions.length }}</span>
      </div>

      <div class="quiz-section-badge">{{ sectionLabel }}</div>

      <div class="quiz-card">
        <div class="question-text">{{ currentQuestion.question }}</div>

        <!-- 单选题（逻辑/职业倾向） -->
        <div class="options-list" v-if="currentQuestion.type === 'single'">
          <button
            v-for="(opt, idx) in currentQuestion.options"
            :key="idx"
            class="option-btn"
            :class="{ selected: answers[currentQuestion.q_id] === optKey(idx) }"
            @click="selectOption(currentQuestion.q_id, optKey(idx))"
          >
            {{ opt }}
          </button>
        </div>

        <!-- 技术自评（1-5评分） -->
        <div class="rating-input" v-else-if="currentQuestion.type === 'rating'">
          <p class="rating-desc">请为自己在此项的掌握程度打分：</p>
          <div class="rating-row">
            <span class="rating-label">完全不会</span>
            <button
              v-for="i in 5"
              :key="i"
              class="rating-btn"
              :class="{ active: answers[currentQuestion.q_id] === String(i) }"
              @click="selectOption(currentQuestion.q_id, String(i))"
            >{{ i }}</button>
            <span class="rating-label">非常熟练</span>
          </div>
        </div>
      </div>

      <div class="quiz-nav">
        <button class="nav-btn prev-btn" :disabled="currentIndex === 0" @click="prevQuestion">← 上一题</button>
        <button
          class="nav-btn next-btn"
          @click="nextQuestion"
          :disabled="!answers[currentQuestion.q_id]"
        >
          {{ currentIndex === allQuestions.length - 1 ? '提交测评' : '下一题 →' }}
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div class="assessment-loading" v-if="phase === 'submitting'">
      <div class="loading-spinner"></div>
      <p>正在分析测评结果...</p>
    </div>

    <!-- 结果展示 -->
    <div class="assessment-result" v-if="phase === 'result' && result">
      <div class="result-header">
        <h2>测评完成</h2>
        <div class="overall-score">
          <span class="score-num">{{ result.overall }}</span>
          <span class="score-label">综合得分</span>
        </div>
      </div>

      <div class="result-cards">
        <div class="result-card">
          <div class="result-card-title">逻辑推理</div>
          <div class="result-score-bar">
            <div class="bar-fill" :style="{ width: result.logic_score + '%', background: scoreColor(result.logic_score) }"></div>
          </div>
          <div class="result-score-num">{{ result.logic_score }}<span>/100</span></div>
        </div>

        <div class="result-card" v-for="(score, dim) in result.tech_scores" :key="dim">
          <div class="result-card-title">{{ dim }}</div>
          <div class="result-score-bar">
            <div class="bar-fill" :style="{ width: score + '%', background: scoreColor(score) }"></div>
          </div>
          <div class="result-score-num">{{ score }}<span>/100</span></div>
        </div>
      </div>

      <!-- 职业倾向 -->
      <div class="tendency-card" v-if="topTendencies.length">
        <h3>职业倾向分析</h3>
        <div class="tendency-tags">
          <span class="tendency-tag" v-for="(t, idx) in topTendencies" :key="idx">
            {{ t.dim }} <span class="tendency-count">×{{ t.count }}</span>
          </span>
        </div>
      </div>

      <!-- 能力雷达图 -->
      <div class="radar-card" v-if="result.merged_ability_profile">
        <h3>更新后的能力画像</h3>
        <div ref="radarRef" class="radar-box"></div>
      </div>

      <div class="result-actions">
        <div class="sync-hint" v-if="result.profile_updated">
          <span class="sync-icon">✓</span> 测评结果已同步到你的学生画像（权重 40%）
        </div>
        <button class="primary-btn" @click="$router.push('/portrait')">查看学生画像 →</button>
        <button class="secondary-btn" @click="resetAssessment">重新测评</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, nextTick } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import { Message } from '@arco-design/web-vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
// import { assessmentApi } from '../api/assessment'  // 测评功能暂时隐藏
const assessmentApi = { getQuestions: (_: string): Promise<any> => Promise.resolve({ logic: [] as any[], career_tendency: [] as any[], tech_self_assessment: [] as any[], tech_job_hint: '' }), submit: (_: any): Promise<any> => Promise.resolve({ logic_score: 0, tendency_dimensions: {}, tech_scores: {}, ability_profile_update: {}, overall: 0 }) }

const userStore = useUserStore()

type Phase = 'start' | 'quiz' | 'submitting' | 'result'
const phase = ref<Phase>('start')
const jobHint = ref('')
const loadingQ = ref(false)
const allQuestions = ref<any[]>([])
const currentIndex = ref(0)
const answers = ref<Record<string, string>>({})
const result = ref<any>(null)
const radarRef = ref<HTMLDivElement | null>(null)
let radarChart: ECharts | null = null

const currentQuestion = computed(() => allQuestions.value[currentIndex.value] || null)
const progressPct = computed(() => allQuestions.value.length ? Math.round((currentIndex.value / allQuestions.value.length) * 100) : 0)

const sectionLabel = computed(() => {
  const q = currentQuestion.value
  if (!q) return ''
  const qid = q.q_id || ''
  if (qid.startsWith('L')) return '第一部分：逻辑推理'
  if (qid.startsWith('C')) return '第二部分：职业倾向'
  return '第三部分：技术自评'
})

const topTendencies = computed(() => {
  if (!result.value?.tendency_dimensions) return []
  return Object.entries(result.value.tendency_dimensions as Record<string, number>)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4)
    .map(([dim, count]) => ({ dim, count }))
})

function optKey(idx: number | string): string {
  return ['A', 'B', 'C', 'D'][Number(idx)]
}

function scoreColor(score: number): string {
  if (score >= 70) return '#52c41a'
  if (score >= 50) return '#faad14'
  return '#ff4d4f'
}

async function startAssessment() {
  loadingQ.value = true
  try {
    const data = await assessmentApi.getQuestions(jobHint.value)
    const questions: any[] = []
    // 逻辑推理
    for (const q of data.logic || []) {
      questions.push({ ...q, type: 'single' })
    }
    // 职业倾向
    for (const q of data.career_tendency || []) {
      questions.push({ ...q, type: 'single' })
    }
    // 技术自评（转为 rating 类型）
    for (const q of data.tech_self_assessment || []) {
      questions.push({ ...q, type: 'rating' })
    }
    allQuestions.value = questions
    phase.value = 'quiz'
    currentIndex.value = 0
    answers.value = {}
  } catch (e: any) {
    Message.error('题目加载失败：' + (e.message || '请重试'))
  } finally {
    loadingQ.value = false
  }
}

function selectOption(qId: string, value: string) {
  answers.value = { ...answers.value, [qId]: value }
}

function prevQuestion() {
  if (currentIndex.value > 0) currentIndex.value--
}

async function nextQuestion() {
  if (currentIndex.value < allQuestions.value.length - 1) {
    currentIndex.value++
  } else {
    await submitAssessment()
  }
}

async function submitAssessment() {
  phase.value = 'submitting'
  try {
    const answerList = Object.entries(answers.value).map(([q_id, answer]) => ({ q_id, answer }))
    const res = await assessmentApi.submit({
      student_id: userStore.studentId || null,
      answers: answerList,
      job_hint: jobHint.value,
    })
    result.value = res
    phase.value = 'result'
    await nextTick()
    renderRadar()
  } catch (e: any) {
    Message.error('提交失败：' + (e.message || '请重试'))
    phase.value = 'quiz'
  }
}

function renderRadar() {
  if (!radarRef.value || !result.value?.merged_ability_profile) return
  radarChart?.dispose()
  radarChart = echarts.init(radarRef.value)
  const dims = Object.entries(result.value.merged_ability_profile as Record<string, number>)
  radarChart.setOption({
    radar: {
      indicator: dims.map(([name]) => ({ name, max: 100 })),
      shape: 'circle',
    },
    series: [{
      type: 'radar',
      data: [{
        value: dims.map(([, v]) => v),
        name: '能力画像',
        areaStyle: { color: 'rgba(102,126,234,0.2)' },
        lineStyle: { color: '#667eea' },
        itemStyle: { color: '#667eea' },
      }],
    }],
  })
}

function resetAssessment() {
  phase.value = 'start'
  allQuestions.value = []
  answers.value = {}
  result.value = null
  currentIndex.value = 0
}

onUnmounted(() => {
  radarChart?.dispose()
})
</script>

<style scoped>
/* ── 开始页 ── */
.assessment-start {
  display: flex;
  justify-content: center;
  padding: 60px 24px;
}

.start-card {
  background: white;
  border-radius: 20px;
  padding: 48px;
  max-width: 560px;
  width: 100%;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.start-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.start-card h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.start-card p {
  font-size: 15px;
  color: #555;
  line-height: 1.8;
  margin-bottom: 12px;
}

.hint-text {
  color: #999;
  font-size: 13px;
}

.job-hint-row {
  margin: 24px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.job-hint-row label {
  font-size: 14px;
  color: #333;
}

.job-select {
  padding: 10px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.start-btn {
  padding: 14px 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.start-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 答题页 ── */
.assessment-quiz {
  max-width: 680px;
  margin: 0 auto;
  padding: 32px 24px;
}

.quiz-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.progress-bar-track {
  flex: 1;
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 13px;
  color: #999;
  white-space: nowrap;
}

.quiz-section-badge {
  display: inline-block;
  padding: 4px 16px;
  background: #f0f4ff;
  color: #667eea;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 16px;
}

.quiz-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 24px;
}

.question-text {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  line-height: 1.6;
  margin-bottom: 24px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-btn {
  padding: 14px 20px;
  border: 2px solid #eee;
  border-radius: 12px;
  background: white;
  text-align: left;
  font-size: 15px;
  color: #333;
  cursor: pointer;
  transition: all 0.2s;
}

.option-btn:hover {
  border-color: #667eea;
  background: #f0f4ff;
}

.option-btn.selected {
  border-color: #667eea;
  background: #f0f4ff;
  color: #667eea;
  font-weight: 600;
}

.rating-input {
  padding: 8px 0;
}

.rating-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 16px;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rating-label {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
}

.rating-btn {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  border: 2px solid #eee;
  background: white;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  color: #555;
  transition: all 0.2s;
}

.rating-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.rating-btn.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.quiz-nav {
  display: flex;
  justify-content: space-between;
}

.nav-btn {
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.prev-btn {
  background: #f5f5f5;
  color: #666;
}

.prev-btn:hover:not(:disabled) {
  background: #eee;
}

.prev-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.next-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.next-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.next-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 加载中 ── */
.assessment-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 20px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 结果页 ── */
.assessment-result {
  max-width: 680px;
  margin: 0 auto;
  padding: 32px 24px;
}

.result-header {
  text-align: center;
  margin-bottom: 32px;
}

.result-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.overall-score {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  width: 120px;
  height: 120px;
  justify-content: center;
}

.score-num {
  font-size: 36px;
  font-weight: 700;
}

.score-label {
  font-size: 12px;
  opacity: 0.85;
}

.result-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.result-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.result-card-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.result-score-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.result-score-num {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

.result-score-num span {
  font-size: 13px;
  color: #999;
  font-weight: 400;
}

.tendency-card,
.radar-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.tendency-card h3,
.radar-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.tendency-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tendency-tag {
  padding: 8px 16px;
  background: #f0f4ff;
  color: #667eea;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.tendency-count {
  font-weight: 700;
}

.radar-box {
  height: 300px;
}

.result-actions {
  text-align: center;
  padding: 24px 0;
}

.sync-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #52c41a;
  font-size: 14px;
  margin-bottom: 20px;
}

.sync-icon {
  font-size: 18px;
}

.primary-btn {
  padding: 14px 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-right: 12px;
  transition: all 0.2s;
  width: auto;
}

.primary-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.secondary-btn {
  padding: 14px 32px;
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.secondary-btn:hover {
  background: #f0f4ff;
}
</style>
