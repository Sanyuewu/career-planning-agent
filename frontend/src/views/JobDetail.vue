<template>
  <div class="job-detail-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">
        <span>←</span>
      </button>
      <div class="header-content">
        <h1>岗位详情</h1>
      </div>
    </div>

    <div class="detail-container" v-if="!loading">
      <div class="job-main">
        <div class="job-header-card">
          <div class="job-title-section">
            <h2 class="job-title">{{ jobInfo?.title || jobName }}</h2>
            <span class="job-salary">{{ jobInfo?.salary || '面议' }}</span>
          </div>
          <div class="job-meta">
            <span class="meta-item" v-if="jobInfo?.industry">
              <span class="meta-icon">🏢</span>
              {{ jobInfo.industry }}
            </span>
            <span class="meta-item" v-if="jobInfo?.education">
              <span class="meta-icon">🎓</span>
              {{ jobInfo.education }}
            </span>
            <span class="meta-item" v-if="jobInfo?.experience">
              <span class="meta-icon">📅</span>
              {{ jobInfo.experience }}
            </span>
          </div>
        </div>

        <!-- F-4: AI 岗位洞察卡片 -->
        <div class="job-section ai-insight-card" v-if="aiInsight || aiInsightLoading">
          <div class="ai-insight-header">
            <h3>AI 岗位洞察</h3>
            <span class="ai-badge">由 AI 实时生成</span>
          </div>
          <div class="ai-insight-loading" v-if="aiInsightLoading && !aiInsight">
            <span>AI 正在分析中...</span>
          </div>
          <div class="ai-insight-content" v-if="aiInsight">
            <p class="ai-insight-text">{{ aiInsight.insight }}</p>
            <div class="ai-insight-skills" v-if="aiInsight.core_skills?.length">
              <span class="insight-label">核心竞争力：</span>
              <span class="insight-skill-tag" v-for="(skill, idx) in aiInsight.core_skills" :key="idx">{{ skill }}</span>
            </div>
          </div>
        </div>

        <div class="job-section" v-if="jobInfo?.skills?.length">
          <h3>技能要求</h3>
          <div class="skills-list">
            <span class="skill-tag" v-for="(skill, idx) in jobInfo.skills" :key="`skill-${idx}`">
              {{ skill }}
            </span>
          </div>
        </div>

        <div class="job-section" v-if="jobInfo?.overview">
          <h3>岗位描述</h3>
          <p class="overview-text">{{ jobInfo.overview }}</p>
        </div>

        <div class="job-section" v-if="jobInfo?.responsibilities?.length">
          <h3>工作职责</h3>
          <ul class="responsibility-list">
            <li v-for="(resp, idx) in jobInfo.responsibilities" :key="`resp-${idx}`">{{ resp }}</li>
          </ul>
        </div>

        <div class="job-section" v-if="hasAnySoftSkill">
          <h3>能力要求</h3>
          <div class="soft-skills-grid">
            <div class="soft-skill-item" v-if="jobInfo?.innovationReq">
              <span class="soft-skill-label">💡 创新能力</span>
              <span class="soft-skill-value">{{ jobInfo.innovationReq }}</span>
            </div>
            <div class="soft-skill-item" v-if="jobInfo?.learningReq">
              <span class="soft-skill-label">📚 学习能力</span>
              <span class="soft-skill-value">{{ jobInfo.learningReq }}</span>
            </div>
            <div class="soft-skill-item" v-if="jobInfo?.stressReq">
              <span class="soft-skill-label">💪 抗压能力</span>
              <span class="soft-skill-value">{{ jobInfo.stressReq }}</span>
            </div>
            <div class="soft-skill-item" v-if="jobInfo?.communicationReq">
              <span class="soft-skill-label">🗣️ 沟通能力</span>
              <span class="soft-skill-value">{{ jobInfo.communicationReq }}</span>
            </div>
            <div class="soft-skill-item" v-if="jobInfo?.internshipReq">
              <span class="soft-skill-label">🏢 实习要求</span>
              <span class="soft-skill-value">{{ jobInfo.internshipReq }}</span>
            </div>
            <div class="soft-skill-item" v-if="jobInfo?.certRequirements?.length">
              <span class="soft-skill-label">📜 证书要求</span>
              <span class="soft-skill-value">{{ jobInfo.certRequirements.join('、') }}</span>
            </div>
          </div>
        </div>

        <div class="job-section" v-if="careerPaths.promotion_paths?.length">
          <h3>晋升路径</h3>
          <div class="career-path">
            <div class="path-item" v-for="(node, idx) in promotionNodes" :key="`promo-${idx}`">
              <div class="path-node">
                <span class="node-title">{{ node.title }}</span>
                <span class="node-salary" v-if="node.salary">{{ node.salary }}</span>
              </div>
              <div class="path-arrow" v-if="Number(idx) < promotionNodes.length - 1">→</div>
            </div>
          </div>
        </div>

        <div class="job-section" v-if="careerPaths.transfer_paths?.length">
          <h3>转岗路径</h3>
          <div class="transfer-grid">
            <div class="transfer-card" v-for="(path, idx) in (showAllTransfer ? careerPaths.transfer_paths : careerPaths.transfer_paths.slice(0, 3))" :key="`transfer-${idx}`">
              <div class="transfer-header">
                <span class="transfer-title">{{ path.target }}</span>
                <span class="transfer-match" :class="path.match_level">
                  {{ ((path.overlap_pct || 0) * 100).toFixed(0) }}% 匹配
                </span>
              </div>
              <p class="transfer-advantage" v-if="path.advantage">{{ path.advantage }}</p>
              <p class="transfer-need" v-if="path.need_learn">需要学习：{{ path.need_learn }}</p>
            </div>
          </div>
          <button
            v-if="careerPaths.transfer_paths.length > 3"
            class="expand-btn"
            @click="showAllTransfer = !showAllTransfer"
          >
            {{ showAllTransfer ? '收起' : `展开全部 ${careerPaths.transfer_paths.length} 条换岗路径` }}
          </button>
        </div>

        <!-- 行业洞察折叠卡片 -->
        <div class="job-section insight-section" v-if="extendedInfo || trendData">
          <div class="insight-header" @click="showInsights = !showInsights">
            <h3>行业洞察与需求分析</h3>
            <div class="insight-header-right">
              <span class="industry-badge" v-if="trendData?.industry_insight?.industry_name">{{ trendData.industry_insight.industry_name }}</span>
              <span class="growth-badge" v-if="trendData?.industry_insight?.growth_rate">{{ trendData.industry_insight.growth_rate }}</span>
              <span class="toggle-icon">{{ showInsights ? '▲' : '▼' }}</span>
            </div>
          </div>
          <div class="insight-body" v-if="showInsights">

            <!-- 岗位基础信息行 -->
            <div class="insight-meta-row">
              <div class="meta-chip" v-if="extendedInfo?.education_level">
                <span class="chip-label">学历</span>{{ extendedInfo.education_level }}
              </div>
              <div class="meta-chip" v-if="extendedInfo?.majors?.length">
                <span class="chip-label">专业</span>{{ extendedInfo.majors.slice(0,3).join(' / ') }}
              </div>
              <div class="meta-chip" v-if="trendData?.jd_count">
                <span class="chip-label">在招JD</span>{{ trendData.jd_count }} 条
              </div>
              <div class="meta-chip" v-if="trendData?.avg_salary_k">
                <span class="chip-label">均薪</span>{{ trendData.avg_salary_k.toFixed(1) }}K
              </div>
              <div class="meta-chip" v-if="extendedInfo?.market_hotness !== undefined">
                <span class="chip-label">热度</span>
                <span v-for="i in 5" :key="i" :class="i <= extendedInfo.market_hotness ? 'star-on' : 'star-off'">★</span>
              </div>
            </div>

            <!-- 趋势折线图 -->
            <div v-if="trendData?.snapshots?.length" class="trend-chart-wrap">
              <MarketTrendChart :trend-data="trendData.snapshots" :job-name="jobName" />
            </div>

            <!-- 行业深度洞察 -->
            <template v-if="trendData?.industry_insight">
              <div class="insight-divider">
                <span>{{ trendData.industry_insight.industry_name }} 行业深度分析</span>
              </div>

              <!-- 趋势概述 -->
              <div class="insight-overview-row">
                <div class="overview-chip trend-chip">
                  <span class="ov-label">行业趋势</span>
                  <span class="ov-val">{{ trendData.industry_insight.trend }}</span>
                </div>
                <div class="overview-chip">
                  <span class="ov-label">招聘季节</span>
                  <span class="ov-val">{{ trendData.industry_insight.hiring_seasons }}</span>
                </div>
                <div class="overview-chip">
                  <span class="ov-label">竞争比</span>
                  <span class="ov-val">{{ trendData.industry_insight.competitive_ratio }}</span>
                </div>
                <div class="overview-chip">
                  <span class="ov-label">薪资区间</span>
                  <span class="ov-val">{{ trendData.industry_insight.salary_range }}</span>
                </div>
              </div>

              <!-- 驱动 & 挑战 双列 -->
              <div class="dual-col">
                <div class="dual-card drivers-card">
                  <div class="dual-title">🚀 增长驱动</div>
                  <ul>
                    <li v-for="(d, i) in trendData.industry_insight.drivers" :key="i">{{ d }}</li>
                  </ul>
                </div>
                <div class="dual-card challenges-card">
                  <div class="dual-title">⚡ 主要挑战</div>
                  <ul>
                    <li v-for="(c, i) in trendData.industry_insight.challenges" :key="i">{{ c }}</li>
                  </ul>
                </div>
              </div>

              <!-- 热门技能 -->
              <div class="insight-block" v-if="trendData.industry_insight.hot_skills?.length">
                <div class="block-title">🔥 行业热门技能</div>
                <div class="hot-skills-wrap">
                  <span class="hot-skill-tag" v-for="(s, i) in trendData.industry_insight.hot_skills" :key="i">{{ s }}</span>
                </div>
              </div>

              <!-- 面试重点 -->
              <div class="insight-block" v-if="trendData.industry_insight.interview_focus">
                <div class="block-title">🎯 面试重点</div>
                <p class="block-text">{{ trendData.industry_insight.interview_focus }}</p>
              </div>

              <!-- 前景展望 -->
              <div class="insight-block" v-if="trendData.industry_insight.future">
                <div class="block-title">🔭 未来展望</div>
                <p class="block-text">{{ trendData.industry_insight.future }}</p>
              </div>

              <!-- 主要城市 -->
              <div class="insight-block" v-if="trendData.industry_insight.top_cities?.length">
                <div class="block-title">📍 主要需求城市</div>
                <div class="cities-wrap">
                  <span class="city-tag" v-for="(c, i) in trendData.industry_insight.top_cities" :key="i">{{ c }}</span>
                </div>
              </div>
            </template>

            <!-- 热门招聘企业 -->
            <div class="insight-block" v-if="trendData?.top_companies?.length">
              <div class="block-title">🏢 热门招聘企业</div>
              <div class="companies-inline">
                <span class="company-tag-sm" v-for="(c, i) in trendData.top_companies" :key="i">{{ c }}</span>
              </div>
            </div>

          </div>
        </div>
      </div>

      <div class="job-sidebar">
        <div class="action-card">
          <h3>开始职业匹配</h3>
          <p>上传简历后，AI将分析您与该岗位的匹配度</p>
          
          <!-- 快速分析按钮 (CrewAI) -->
          <button 
            v-if="crewAIEnabled && userStore.isLoggedIn && userStore.studentId" 
            class="quick-analysis-btn"
            @click="startQuickAnalysis"
            :disabled="crewStore.isProcessing"
          >
            <span>⚡</span>
            {{ crewStore.isProcessing ? '分析中...' : 'AI快速分析' }}
          </button>
          
          <button class="primary-btn" @click="handleStartMatch">
            <span>🎯</span>
            {{ userStore.isLoggedIn ? '开始匹配分析' : '登录后开始匹配' }}
          </button>
          <p class="login-hint" v-if="!userStore.isLoggedIn">
            需要先登录并上传简历
          </p>
        </div>
        
        <!-- 快速分析进度 -->
        <AsyncTaskProgress
          v-if="showQuickAnalysis && crewStore.isProcessing"
          :visible="showQuickAnalysis"
          title="⚡ AI快速分析"
          description="正在分析您的简历与岗位匹配度..."
          :progress="crewStore.progress"
          status="running"
          @cancel="showQuickAnalysis = false"
        />
        
        <!-- 快速分析结果 -->
        <div class="quick-result-card" v-if="quickAnalysisResult && !crewStore.isProcessing">
          <h3>分析结果</h3>
          <div class="result-summary" v-if="quickAnalysisResult.resume_analysis">
            <p class="result-score" v-if="quickAnalysisResult.resume_analysis.match_score">
              匹配度: <strong>{{ (quickAnalysisResult.resume_analysis.match_score * 100).toFixed(0) }}%</strong>
            </p>
            <p class="result-hint" v-if="quickAnalysisResult.resume_analysis.summary">
              {{ quickAnalysisResult.resume_analysis.summary }}
            </p>
          </div>
          <button class="view-detail-btn" @click="goToFullMatch">
            查看完整分析 →
          </button>
        </div>

        <div class="market-card" v-if="marketData.jd_count > 0">
          <h3>市场数据</h3>
          <div class="market-stats">
            <div class="stat-item">
              <span class="stat-value">{{ marketData.jd_count }}</span>
              <span class="stat-label">在招岗位</span>
            </div>
            <div class="stat-item" v-if="marketData.avg_salary_k > 0">
              <span class="stat-value">{{ marketData.avg_salary_k.toFixed(1) }}K</span>
              <span class="stat-label">平均月薪</span>
            </div>
          </div>
          <div class="top-companies" v-if="marketData.top_companies?.length">
            <span class="companies-label">热门招聘企业：</span>
            <span class="company-tag" v-for="(c, idx) in marketData.top_companies.slice(0, 5)" :key="`company-${idx}`">{{ c }}</span>
          </div>
        </div>

        <div class="regions-card" v-if="extendedInfo?.top_regions?.length">
          <h3>主要就业城市</h3>
          <div class="regions-list">
            <span class="region-tag" v-for="(r, idx) in extendedInfo.top_regions" :key="`region-${idx}`">{{ r }}</span>
          </div>
        </div>

        <div class="culture-card" v-if="extendedInfo?.culture_types?.length">
          <h3>企业文化类型</h3>
          <div class="culture-list">
            <span class="culture-tag" v-for="(c, idx) in extendedInfo.culture_types" :key="`culture-${idx}`">{{ c }}</span>
          </div>
        </div>

        <div class="related-card" v-if="relatedJobs.length">
          <h3>相关岗位</h3>
          <div class="related-list">
            <div class="related-item" v-for="(job, idx) in relatedJobs" :key="`related-${idx}`" @click="goToJob(job)">
              {{ job }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="loading-state" v-else-if="loadError">
      <div class="error-content">
        <p>加载失败</p>
        <button class="retry-btn" @click="loadJobData">🔄 重试</button>
      </div>
    </div>

    <div class="loading-state" v-else>
      <div class="loading-spinner"></div>
      <p>加载岗位信息...</p>
    </div>

    <LoginModal
      v-if="showLoginModal"
      :redirect-path="`/jobs/${jobName}`"
      @close="showLoginModal = false"
      @success="handleLoginSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useUserStore } from '../stores/useUserStore'
import { useCrewStore } from '../stores/useCrewStore'
import { jobApi } from '../api/job'
import { crewApi } from '../api/crew'
import LoginModal from '../components/LoginModal.vue'
import AsyncTaskProgress from '../components/AsyncTaskProgress.vue'
import MarketTrendChart from '../components/MarketTrendChart.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const crewStore = useCrewStore()

const jobName = computed(() => decodeURIComponent(route.params.jobId as string || ''))
const loading = ref(true)
const loadError = ref(false)
const jobInfo = ref<any>(null)
const extendedInfo = ref<any>(null)
const careerPaths = ref<any>({ promotion_paths: [], transfer_paths: [] })
const marketData = ref<any>({ jd_count: 0, avg_salary_k: 0, top_companies: [] })
const relatedJobs = ref<string[]>([])
const showLoginModal = ref(false)
const showAllTransfer = ref(false)
const crewAIEnabled = ref(false)
const showQuickAnalysis = ref(false)
const quickAnalysisResult = ref<any>(null)
const trendData = ref<any>(null)
const showInsights = ref(false)
const aiInsight = ref<any>(null)
const aiInsightLoading = ref(false)

const promotionNodes = computed(() => {
  const paths = careerPaths.value.promotion_paths || []
  if (paths.length === 0) return []
  const firstPath = paths[0]
  return firstPath.nodes || []
})

const hasAnySoftSkill = computed(() => {
  const j = jobInfo.value
  if (!j) return false
  return !!(j.innovationReq || j.learningReq || j.stressReq || j.communicationReq || j.internshipReq || j.certRequirements?.length)
})

async function loadJobData() {
  if (!jobName.value) return
  
  loading.value = true
  loadError.value = false
  try {
    const graph = await import('../graph/job_graph_repo').then(m => m.jobGraph)
    jobInfo.value = graph.getJobInfo(jobName.value)
    
    const paths = await jobApi.getCareerGraph(jobName.value)
    careerPaths.value = paths || { promotion_paths: [], transfer_paths: [] }

    // 加载扩展信息（top_regions / culture_types / majors / tags）
    try {
      extendedInfo.value = await jobApi.getJobInfo(jobName.value)
    } catch {
      extendedInfo.value = null
    }

    try {
      const market = await jobApi.getRealJobs(jobName.value, 5)
      marketData.value = market
    } catch {
      marketData.value = { jd_count: 0, avg_salary_k: 0, top_companies: [] }
    }

    // 加载行业趋势数据
    try {
      const trend = await jobApi.getMarketTrend(jobName.value)
      trendData.value = trend
    } catch {
      trendData.value = null
    }

    // F-4: 异步加载 AI 岗位洞察（不阻塞主流程）
    aiInsightLoading.value = true
    jobApi.getAiInsight(jobName.value).then(res => {
      aiInsight.value = res
    }).catch(() => {
      aiInsight.value = null
    }).finally(() => {
      aiInsightLoading.value = false
    })

    const allJobs = await import('../api/match').then(m => m.matchApi.getJobs())
    const currentTitle = jobName.value.toLowerCase()
    relatedJobs.value = allJobs
      .filter((j: string) => j.toLowerCase() !== currentTitle)
      .slice(0, 5)
  } catch (e) {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function handleStartMatch() {
  if (!userStore.isLoggedIn) {
    showLoginModal.value = true
    return
  }
  
  if (!userStore.studentId) {
    router.push({ path: '/upload', query: { job: jobName.value } })
    return
  }
  
  router.push({ path: '/match', query: { job: jobName.value } })
}

function handleLoginSuccess() {
  showLoginModal.value = false
  if (userStore.studentId) {
    router.push({ path: '/match', query: { job: jobName.value } })
  } else {
    router.push({ path: '/upload', query: { job: jobName.value } })
  }
}

function goToJob(title: string) {
  router.push(`/jobs/${encodeURIComponent(title)}`)
}

async function checkCrewAIStatus() {
  try {
    const status = await crewApi.getStatus()
    crewAIEnabled.value = status.crewai_installed && status.llm_configured
  } catch {
    crewAIEnabled.value = false
  }
}

async function startQuickAnalysis() {
  if (!userStore.isLoggedIn) {
    showLoginModal.value = true
    return
  }
  
  if (!userStore.studentId) {
    Message.warning('请先上传简历')
    router.push({ path: '/upload', query: { job: jobName.value } })
    return
  }
  
  showQuickAnalysis.value = true
  
  try {
    const result = await crewStore.runAnalysis({
      resume_content: '',
      parsed_data: {
        student_id: userStore.studentId
      }
    })
    
    if (result.success && result.results) {
      quickAnalysisResult.value = result.results
      Message.success('快速分析完成！')
    }
  } catch (e: any) {
    Message.error(e.message || '快速分析失败')
  }
}

function goToFullMatch() {
  router.push({ path: '/match', query: { job: jobName.value } })
}

watch(jobName, () => {
  loadJobData()
  checkCrewAIStatus()
}, { immediate: true })
</script>

<style scoped>
.job-detail-page {
  min-height: 100vh;
  background: #f8fafc;
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

.detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
}

.job-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.job-header-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.job-title-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.job-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.job-salary {
  font-size: 24px;
  font-weight: 700;
  color: #52c41a;
}

.job-meta {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #666;
}

.meta-icon {
  font-size: 16px;
}

.job-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.job-section h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.ai-insight-card {
  border: 1px solid #e8f4ff;
  background: linear-gradient(135deg, #f0f7ff 0%, #fff 100%);
}

.ai-insight-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.ai-insight-header h3 {
  margin: 0;
}

.ai-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 10px;
  font-weight: 500;
}

.ai-insight-loading {
  color: #999;
  font-size: 14px;
  padding: 8px 0;
}

.ai-insight-text {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  margin-bottom: 12px;
}

.ai-insight-skills {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.insight-label {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}

.insight-skill-tag {
  padding: 4px 12px;
  background: #e8f0fe;
  color: #1677ff;
  border-radius: 12px;
  font-size: 13px;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.skill-tag {
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 14px;
}

.overview-text {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
  margin: 0;
}

.responsibility-list {
  margin: 0;
  padding-left: 20px;
}

.responsibility-list li {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  margin-bottom: 8px;
}

.soft-skills-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.soft-skill-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
}

.soft-skill-label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
}

.soft-skill-value {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}

.career-path {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.path-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-node {
  background: #f0f4ff;
  border-radius: 12px;
  padding: 12px 20px;
  text-align: center;
}

.node-title {
  display: block;
  font-weight: 600;
  color: #1a1a2e;
  font-size: 14px;
}

.node-salary {
  display: block;
  font-size: 12px;
  color: #52c41a;
  margin-top: 4px;
}

.path-arrow {
  color: #667eea;
  font-size: 20px;
}

.transfer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.transfer-card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #eee;
}

.transfer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.transfer-title {
  font-weight: 600;
  color: #1a1a2e;
}

.transfer-match {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.transfer-match.high { background: #f6ffed; color: #52c41a; }
.transfer-match.medium { background: #e6f7ff; color: #1890ff; }
.transfer-match.low { background: #fff7e6; color: #fa8c16; }

.transfer-advantage, .transfer-need {
  font-size: 12px;
  color: #666;
  margin: 4px 0 0;
}

.expand-btn {
  margin-top: 12px;
  padding: 6px 16px;
  background: none;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #1890ff;
  transition: border-color 0.2s;
}
.expand-btn:hover { border-color: #1890ff; }

.job-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.action-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
}

.action-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.action-card p {
  font-size: 14px;
  color: #666;
  margin: 0 0 20px;
}

.primary-btn {
  width: 100%;
  padding: 14px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.primary-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
}

.quick-analysis-btn {
  width: 100%;
  padding: 12px 24px;
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  margin-bottom: 12px;
}

.quick-analysis-btn:hover:not(:disabled) {
  background: #f0f4ff;
  transform: translateY(-1px);
}

.quick-analysis-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.quick-result-card {
  background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  border: 1px solid #e0e8ff;
}

.quick-result-card h3 {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px;
}

.result-summary {
  margin-bottom: 12px;
}

.result-score {
  font-size: 14px;
  color: #666;
  margin: 0 0 8px;
}

.result-score strong {
  color: #667eea;
  font-size: 18px;
}

.result-hint {
  font-size: 13px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.view-detail-btn {
  width: 100%;
  padding: 10px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.view-detail-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.login-hint {
  font-size: 12px;
  color: #999;
  margin-top: 12px;
}

.market-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.market-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.market-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #667eea;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

.top-companies {
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.companies-label {
  font-size: 12px;
  color: #999;
  display: block;
  margin-bottom: 8px;
}

.company-tag {
  display: inline-block;
  background: #f0f4ff;
  color: #667eea;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  margin-right: 6px;
  margin-bottom: 6px;
}

.regions-card, .culture-card {
  background: white;
  border-radius: 16px;
  padding: 20px 24px;
}

.regions-card h3, .culture-card h3 {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 12px;
}

.regions-list, .culture-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.region-tag {
  padding: 4px 12px;
  background: #e6f7ff;
  color: #0958d9;
  border-radius: 20px;
  font-size: 13px;
}

.culture-tag {
  padding: 4px 12px;
  background: #f6ffed;
  color: #389e0d;
  border-radius: 20px;
  font-size: 13px;
}

.related-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.related-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.related-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.related-item {
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 10px;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  transition: all 0.2s;
}

.related-item:hover {
  background: #f0f4ff;
  color: #667eea;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.insight-section { cursor: default; }
.insight-header {
  display: flex; justify-content: space-between; align-items: center;
  cursor: pointer; user-select: none;
}
.insight-header h3 { margin: 0; }
.insight-header-right { display: flex; align-items: center; gap: 8px; }
.toggle-icon { color: #999; font-size: 12px; }
.industry-badge { padding: 2px 10px; background: #f0f4ff; color: #667eea; border-radius: 10px; font-size: 12px; font-weight: 500; }
.growth-badge { padding: 2px 10px; background: #f6ffed; color: #52c41a; border-radius: 10px; font-size: 12px; font-weight: 600; }
.insight-body { margin-top: 16px; display: flex; flex-direction: column; gap: 16px; }

.insight-meta-row { display: flex; flex-wrap: wrap; gap: 10px; }
.meta-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; background: #f8f9fa; border-radius: 8px; font-size: 13px; color: #333;
}
.chip-label { font-size: 11px; color: #999; margin-right: 2px; }
.star-on { color: #faad14; }
.star-off { color: #ddd; }
.trend-chart-wrap { height: 220px; }

.insight-divider {
  display: flex; align-items: center; gap: 12px;
  color: #999; font-size: 13px; font-weight: 500;
}
.insight-divider::before, .insight-divider::after {
  content: ''; flex: 1; height: 1px; background: #f0f0f0;
}

.insight-overview-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.overview-chip {
  background: #f8fafc; border-radius: 10px; padding: 10px 14px;
  display: flex; flex-direction: column; gap: 4px;
}
.trend-chip { background: linear-gradient(135deg, #f0f4ff, #faf0ff); }
.ov-label { font-size: 11px; color: #999; }
.ov-val { font-size: 13px; color: #333; font-weight: 600; line-height: 1.4; }

.dual-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.dual-card { border-radius: 10px; padding: 14px 16px; }
.drivers-card { background: #f6ffed; border: 1px solid #d9f7be; }
.challenges-card { background: #fff7e6; border: 1px solid #ffd591; }
.dual-title { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px; }
.dual-card ul { margin: 0; padding-left: 16px; }
.dual-card li { font-size: 13px; color: #555; line-height: 1.8; }

.insight-block { display: flex; flex-direction: column; gap: 8px; }
.block-title { font-size: 13px; font-weight: 600; color: #333; }
.block-text { font-size: 13px; color: #555; line-height: 1.7; margin: 0; background: #f8f9fa; border-radius: 8px; padding: 10px 14px; border-left: 3px solid #667eea; }

.hot-skills-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
.hot-skill-tag { padding: 4px 12px; background: linear-gradient(135deg, #667eea22, #764ba222); color: #5a67d8; border-radius: 16px; font-size: 12px; font-weight: 500; border: 1px solid #667eea33; }

.cities-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
.city-tag { padding: 4px 12px; background: #e6f7ff; color: #0958d9; border-radius: 20px; font-size: 13px; }

.companies-inline { display: flex; flex-wrap: wrap; gap: 8px; }
.company-tag-sm { padding: 4px 10px; background: #f0f4ff; color: #667eea; border-radius: 6px; font-size: 12px; }

@media (max-width: 768px) {
  .dual-col { grid-template-columns: 1fr; }
  .insight-overview-row { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 1024px) {
  .detail-container {
    grid-template-columns: 1fr;
  }

  .job-sidebar {
    order: -1;
  }
}
</style>
