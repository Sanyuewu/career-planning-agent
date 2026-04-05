<template>
  <div class="home-page">
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">🚀 AI智能驱动</div>
        <h1 class="hero-title">
          <span class="gradient-text">AI大学生</span>
          <br />
          职业规划智能体
        </h1>
        <p class="hero-subtitle">
          基于语义图谱的智能人岗匹配与职业发展规划系统
        </p>
        <div class="hero-actions">
          <a-button v-if="!userStore.isCompany && !userStore.isAdmin" type="primary" size="large" class="start-btn" @click="scrollToJobs">
            <template #icon>🎯</template>
            浏览岗位
          </a-button>
          <template v-if="!userStore.isLoggedIn">
            <a-button size="large" class="login-btn" @click="goTo('/login')">
              <template #icon>🔑</template>
              登录/注册
            </a-button>
          </template>
          <template v-else-if="userStore.isCompany">
            <a-button type="primary" size="large" class="company-btn" @click="goTo('/company')">
              <template #icon>🏢</template>
              进入工作台
            </a-button>
          </template>
          <template v-else-if="userStore.isAdmin">
            <a-button type="primary" size="large" class="admin-btn" @click="goTo('/admin')">
              <template #icon>⚙️</template>
              进入管理后台
            </a-button>
          </template>
          <template v-else>
            <a-button size="large" class="demo-btn" @click="goTo('/match')">
              <template #icon>📊</template>
              开始匹配
            </a-button>
          </template>
        </div>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-value">{{ platformStats.studentCount || jobStats.total }}</span>
            <span class="stat-label">服务学生</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ platformStats.jobCount || jobStats.total }}</span>
            <span class="stat-label">覆盖岗位</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ platformStats.jdTotal ? platformStats.jdTotal.toLocaleString() : '—' }}</span>
            <span class="stat-label">真实招聘数据</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ platformStats.reportCount ?? '—' }}</span>
            <span class="stat-label">生成报告</span>
          </div>
        </div>
      </div>
    </div>

    <div class="dashboard-section" v-if="userStore.isLoggedIn && !userStore.isCompany && !userStore.isAdmin">
      <div class="dashboard-grid">
        <div class="dashboard-left">
          <UserStatsCard />
        </div>
        <div class="dashboard-right">
          <PersonalizedRecommend />
        </div>
      </div>
    </div>

    <div class="jobs-section" ref="jobsSectionRef" v-if="!userStore.isCompany && !userStore.isAdmin">
      <div class="section-header">
        <h2>热门岗位</h2>
        <p>探索适合你的职业方向，点击查看详情</p>
        
        <!-- AI智能推荐入口 -->
        <div class="ai-recommend-entry" v-if="userStore.isLoggedIn && userStore.studentId">
          <button 
            class="ai-recommend-btn" 
            @click="startAIRecommend"
            :disabled="aiRecommendLoading"
          >
            <span class="btn-icon">🤖</span>
            <span class="btn-text">{{ aiRecommendLoading ? 'AI分析中...' : 'AI智能推荐' }}</span>
          </button>
          <p class="ai-hint">基于您的简历画像，为您推荐最匹配的岗位</p>
        </div>
        
        <!-- AI推荐结果 -->
        <div class="ai-recommend-results" v-if="aiRecommendJobs.length > 0">
          <h3>🎯 为您推荐</h3>
          <div class="recommend-grid">
            <div 
              v-for="job in aiRecommendJobs" 
              :key="job.job_title"
              class="recommend-card"
              @click="goToJobDetail(job.job_title)"
            >
              <div class="rec-header">
                <span class="rec-title">{{ job.job_title }}</span>
                <span class="rec-score">{{ job.score.toFixed(0) }}分</span>
              </div>
              <p class="rec-summary">{{ job.summary }}</p>
              <div class="rec-skills" v-if="job.matched_skills?.length">
                <span class="rec-skill" v-for="(s, idx) in job.matched_skills.slice(0, 3)" :key="`rec-skill-${idx}`">{{ s }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="search-box">
          <input
            v-model="searchQuery"
            placeholder="搜索岗位名称..."
            @input="handleSearch"
          />
          <span class="search-icon">🔍</span>
        </div>
      </div>

      <div class="jobs-filter">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['filter-btn', { active: activeCategory === cat.key }]"
          @click="activeCategory = cat.key"
        >
          {{ cat.label }}
        </button>
      </div>

      <div class="jobs-grid" v-if="!loadingJobs">
        <div
          v-for="job in filteredJobs"
          :key="job.title"
          class="job-card"
          @click="goToJobDetail(job.title)"
        >
          <div class="job-header">
            <h3 class="job-title">{{ job.title }}</h3>
            <span class="job-salary">{{ job.salary || '面议' }}</span>
          </div>
          <div class="job-industry" v-if="job.industry">
            <span class="industry-tag">{{ job.industry }}</span>
          </div>
          <div class="job-skills" v-if="job.skills?.length">
            <span class="skill-tag" v-for="(skill, idx) in job.skills.slice(0, 5)" :key="`skill-${idx}`">
              {{ skill }}
            </span>
            <span class="skill-more" v-if="job.skills.length > 5">+{{ job.skills.length - 5 }}</span>
          </div>
          <div class="job-footer">
            <span class="job-demand" v-if="job.demandLevel">
              <span class="demand-dot" :class="job.demandLevel"></span>
              {{ demandLabels[job.demandLevel] || '需求一般' }}
            </span>
            <span class="job-action">
              查看详情 →
            </span>
          </div>
        </div>
      </div>

      <div class="jobs-loading" v-else>
        <div class="loading-spinner"></div>
        <p>加载岗位数据中...</p>
      </div>

      <div class="jobs-empty" v-if="!loadingJobs && filteredJobs.length === 0">
        <p>暂无匹配的岗位，请尝试其他搜索条件</p>
      </div>

      <div class="load-more-wrap" v-if="!loadingJobs && hasMoreJobs">
        <button class="load-more-btn" @click="loadMoreJobs">
          加载更多岗位（还有 {{ allFilteredJobs.length - filteredJobs.length }} 个）
        </button>
      </div>
    </div>

    <div class="features-section" v-if="!userStore.isCompany && !userStore.isAdmin">
      <div class="section-header">
        <h2>核心功能</h2>
        <p>一站式职业规划解决方案</p>
      </div>
      
      <div class="features-grid">
        <div class="feature-card" @click="handleFeatureClick('upload')">
          <div class="feature-icon">📄</div>
          <h3>简历解析</h3>
          <p>支持PDF/DOCX/图片格式，智能提取简历信息，自动生成七维度画像</p>
          <div class="feature-tags">
            <span class="tag">多格式支持</span>
            <span class="tag">智能提取</span>
          </div>
        </div>
        
        <div class="feature-card" @click="handleFeatureClick('match')">
          <div class="feature-icon">🎯</div>
          <h3>人岗匹配</h3>
          <p>五维度匹配评估（含市场需求），语义图谱技能扩展，精准定位职业方向</p>
          <div class="feature-tags">
            <span class="tag">五维评估</span>
            <span class="tag">语义扩展</span>
          </div>
        </div>
        
        <div class="feature-card" @click="handleFeatureClick('report')">
          <div class="feature-icon">📊</div>
          <h3>职业报告</h3>
          <p>个性化职业发展报告，包含行动计划和技能差距分析</p>
          <div class="feature-tags">
            <span class="tag">可导出</span>
            <span class="tag">个性化</span>
          </div>
        </div>
        
        <div class="feature-card" @click="handleFeatureClick('chat')">
          <div class="feature-icon">💬</div>
          <h3>AI对话</h3>
          <p>智能对话引导，情绪感知与支持，全程陪伴职业规划</p>
          <div class="feature-tags">
            <span class="tag">情绪感知</span>
            <span class="tag">智能引导</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 企业用户专属首页 -->
    <div class="company-home" v-if="userStore.isCompany">
      <div class="section-header">
        <h2>企业工作台</h2>
        <p>发布岗位 · 反向寻才 · 市场数据洞察</p>
      </div>
      <div class="company-cards">
        <div class="company-card" @click="goTo('/company')">
          <div class="company-card-icon">📋</div>
          <h3>岗位管理</h3>
          <p>发布、编辑岗位信息，实时查看招聘状态</p>
        </div>
        <div class="company-card" @click="goTo('/company')">
          <div class="company-card-icon">🔍</div>
          <h3>反向寻才</h3>
          <p>输入岗位需求，智能匹配最优候选人画像</p>
        </div>
        <div class="company-card" @click="goTo('/company')">
          <div class="company-card-icon">📈</div>
          <h3>市场洞察</h3>
          <p>岗位薪资分布、人才供需趋势，辅助招聘决策</p>
        </div>
        <div class="company-card" @click="goTo('/company')">
          <div class="company-card-icon">🏢</div>
          <h3>企业档案</h3>
          <p>完善公司信息，提升候选人信任度</p>
        </div>
      </div>
      <div style="text-align:center;margin-top:24px;">
        <a-button type="primary" size="large" @click="goTo('/company')">进入工作台 →</a-button>
      </div>
    </div>

    <!-- 管理员快捷入口暂时隐藏
    <div class="role-banner admin-banner" v-if="userStore.role === 'admin'">
      <div class="role-banner-inner">
        <div class="role-banner-icon">⚙️</div>
        <div class="role-banner-text">
          <h3>管理后台</h3>
          <p>查看系统数据、管理用户、监控岗位图谱</p>
        </div>
        <button class="role-banner-btn" @click="goTo('/admin')">进入后台 →</button>
      </div>
    </div>
    -->

    <div class="footer-section">
      <p>© 2026 AI职业规划智能体</p>
    </div>

    <LoginModal
      v-if="showLoginModal"
      :redirect-path="loginRedirect"
      @close="showLoginModal = false"
      @success="handleLoginSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useUserStore } from '../stores/useUserStore'
import { matchApi } from '../api/match'
import { request } from '../api/http'
import LoginModal from '../components/LoginModal.vue'
import UserStatsCard from '../components/UserStatsCard.vue'
import PersonalizedRecommend from '../components/PersonalizedRecommend.vue'
import { JOB_CATEGORIES, CATEGORY_MAPPING, DEMAND_LABELS } from '../constants'

const router = useRouter()
const userStore = useUserStore()
const jobsSectionRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const activeCategory = ref('all')
const loadingJobs = ref(true)
const allJobs = ref<any[]>([])
const showLoginModal = ref(false)
const loginRedirect = ref('')
const aiRecommendLoading = ref(false)
const aiRecommendJobs = ref<any[]>([])

const jobStats = ref({
  total: 0,
  hotJobs: 0
})

const platformStats = ref({
  studentCount: 0,
  reportCount: 0,
  jobCount: 0,
  jdTotal: 0,
})

const categories = JOB_CATEGORIES
const demandLabels = DEMAND_LABELS
const categoryMapping = CATEGORY_MAPPING

const jobPageSize = ref(20)

const allFilteredJobs = computed(() => {
  let jobs = allJobs.value

  if (activeCategory.value !== 'all') {
    const keywords = categoryMapping[activeCategory.value] || []
    jobs = jobs.filter(job =>
      keywords.some(kw =>
        job.title?.toLowerCase().includes(kw.toLowerCase()) ||
        job.skills?.some((s: string) => s.toLowerCase().includes(kw.toLowerCase()))
      )
    )
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    jobs = jobs.filter(job =>
      job.title?.toLowerCase().includes(q) ||
      job.skills?.some((s: string) => s.toLowerCase().includes(q))
    )
  }

  return jobs
})

const filteredJobs = computed(() => allFilteredJobs.value.slice(0, jobPageSize.value))

const hasMoreJobs = computed(() => allFilteredJobs.value.length > jobPageSize.value)

watch(activeCategory, () => { jobPageSize.value = 20 })

function handleSearch() {
  jobPageSize.value = 20
}

function loadMoreJobs() {
  jobPageSize.value += 20
}

function scrollToJobs() {
  jobsSectionRef.value?.scrollIntoView({ behavior: 'smooth' })
}

function goTo(path: string) {
  router.push(path)
}

function goToJobDetail(jobTitle: string) {
  router.push(`/jobs/${encodeURIComponent(jobTitle)}`)
}

function handleFeatureClick(feature: string) {
  if (!userStore.isLoggedIn && feature !== 'chat') {
    loginRedirect.value = `/${feature}`
    showLoginModal.value = true
    return
  }
  router.push(`/${feature}`)
}

function handleLoginSuccess() {
  showLoginModal.value = false
  if (loginRedirect.value) {
    router.push(loginRedirect.value)
  }
}

async function startAIRecommend() {
  if (!userStore.studentId) {
    Message.warning('请先上传简历')
    router.push('/upload')
    return
  }

  aiRecommendLoading.value = true
  aiRecommendJobs.value = []

  try {
    const result = await matchApi.recommend(userStore.studentId, 3)
    if (result.recommendations?.length) {
      aiRecommendJobs.value = result.recommendations
      Message.success('推荐完成！')
    } else {
      Message.info('暂无推荐结果，请完善简历信息')
    }
  } catch (e: any) {
    Message.error(e.message || '推荐失败')
  } finally {
    aiRecommendLoading.value = false
  }
}

onMounted(async () => {
  // 加载平台真实统计数据
  request.get<any>('/stats/public').then(stats => {
    platformStats.value = {
      studentCount: stats.student_count || 0,
      reportCount: stats.report_count || 0,
      jobCount: stats.job_count || 0,
      jdTotal: stats.jd_total || 0,
    }
  }).catch(() => {})

  try {
    const [jobs, jobGraphMod] = await Promise.all([
      matchApi.getJobs(),
      import('../graph/job_graph_repo').then(m => m.jobGraph),
    ])
    jobStats.value.total = jobs.length
    allJobs.value = jobs.map((title: string) => {
      const info = jobGraphMod.getJobInfo(title)
      return {
        title,
        salary: info?.salary || '面议',
        industry: info?.industry || '',
        skills: info?.skills || [],
        demandLevel: info?.demandLevel || 'medium',
      }
    })
  } catch (e) {
  } finally {
    loadingJobs.value = false
  }
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f8fafc;
}

.hero-section {
  position: relative;
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  z-index: 0;
}

.hero-bg::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
  padding: 40px 20px;
}

.hero-badge {
  display: inline-block;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 14px;
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 20px;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.gradient-text {
  background: linear-gradient(90deg, #fff 0%, #ffd700 50%, #fff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 32px;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 40px;
}

.start-btn {
  background: white !important;
  color: #667eea !important;
  border: none !important;
  font-weight: 600;
  padding: 12px 32px;
  height: auto;
  font-size: 16px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(0, 0, 0, 0.3);
}

.login-btn, .demo-btn {
  background: rgba(255, 255, 255, 0.15) !important;
  color: white !important;
  border: 2px solid rgba(255, 255, 255, 0.5) !important;
  font-weight: 600;
  padding: 12px 32px;
  height: auto;
  font-size: 16px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.hero-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 40px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 32px;
  font-weight: 800;
}

.stat-label {
  font-size: 14px;
  opacity: 0.8;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.3);
}

.jobs-section {
  padding: 60px 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-section {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
}

.dashboard-left {
  min-width: 280px;
}

.dashboard-right {
  min-width: 0;
}

.section-header {
  text-align: center;
  margin-bottom: 40px;
}

.section-header h2 {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.section-header p {
  font-size: 16px;
  color: #666;
  margin-bottom: 24px;
}

.ai-recommend-entry {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}

.ai-recommend-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
}

.ai-recommend-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.4);
}

.ai-recommend-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  font-size: 20px;
}

.ai-hint {
  font-size: 13px;
  color: #999;
  margin: 0;
}

.ai-recommend-results {
  margin-bottom: 32px;
  padding: 24px;
  background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%);
  border-radius: 16px;
  border: 1px solid #e0e8ff;
}

.ai-recommend-results h3 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0 0 16px;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.recommend-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e8e8e8;
}

.recommend-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border-color: #667eea;
}

.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rec-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.rec-score {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
  background: #f0f4ff;
  padding: 4px 10px;
  border-radius: 12px;
}

.rec-summary {
  font-size: 13px;
  color: #666;
  margin: 0 0 10px;
  line-height: 1.5;
}

.rec-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rec-skill {
  font-size: 11px;
  color: #667eea;
  background: #f0f4ff;
  padding: 3px 8px;
  border-radius: 6px;
}

.search-box {
  position: relative;
  max-width: 400px;
  margin: 0 auto;
}

.search-box input {
  width: 100%;
  padding: 14px 20px 14px 48px;
  border: 2px solid #e5e5e5;
  border-radius: 12px;
  font-size: 15px;
  outline: none;
  transition: all 0.2s;
}

.search-box input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
}

.jobs-filter {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 32px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  background: white;
  color: #666;
  border: 1px solid #e5e5e5;
  transition: all 0.2s;
}

.filter-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.filter-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.jobs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.job-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #eee;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.job-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(102, 126, 234, 0.12);
  border-color: #667eea;
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.job-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.job-salary {
  font-size: 16px;
  font-weight: 600;
  color: #52c41a;
}

.job-industry {
  margin-bottom: 12px;
}

.industry-tag {
  background: #f0f4ff;
  color: #667eea;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
}

.job-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.skill-tag {
  background: #f5f5f5;
  color: #666;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.skill-more {
  color: #999;
  font-size: 12px;
  padding: 4px 8px;
}

.job-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.job-demand {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
}

.demand-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.demand-dot.high { background: #52c41a; }
.demand-dot.medium { background: #faad14; }
.demand-dot.low { background: #999; }

.job-action {
  font-size: 14px;
  color: #667eea;
  font-weight: 500;
}

.jobs-loading {
  text-align: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.jobs-empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

.load-more-wrap {
  text-align: center;
  padding: 24px 0 8px;
}

.load-more-btn {
  padding: 10px 32px;
  border: 1.5px solid #4e6ef2;
  border-radius: 20px;
  background: white;
  color: #4e6ef2;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.load-more-btn:hover {
  background: #4e6ef2;
  color: white;
}

.features-section {
  padding: 60px 40px;
  background: white;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: #f8fafc;
  border-radius: 20px;
  padding: 32px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #eee;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.15);
  border-color: #667eea;
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.feature-card p {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 16px;
}

.feature-tags {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.tag {
  background: #e8f4ff;
  color: #1890ff;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.role-banner {
  padding: 20px 40px;
}

.role-banner-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px 32px;
  border-radius: 16px;
}

.company-banner .role-banner-inner {
  background: linear-gradient(135deg, #e6fffb 0%, #f0f9ff 100%);
  border: 1px solid #91d5ff;
}

.admin-banner .role-banner-inner {
  background: linear-gradient(135deg, #fff7e6 0%, #fff2f0 100%);
  border: 1px solid #ffd591;
}

.role-banner-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.role-banner-text {
  flex: 1;
}

.role-banner-text h3 {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 4px;
}

.role-banner-text p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.role-banner-btn {
  padding: 10px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  white-space: nowrap;
  transition: all 0.2s;
}

.company-banner .role-banner-btn {
  background: linear-gradient(135deg, #13c2c2, #096dd9);
  color: white;
}

.admin-banner .role-banner-btn {
  background: linear-gradient(135deg, #fa8c16, #d46b08);
  color: white;
}

.role-banner-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.company-home {
  padding: 40px;
  max-width: 1100px;
  margin: 0 auto;
}

.company-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-top: 24px;
}

@media (max-width: 900px) {
  .company-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

.company-card {
  background: white;
  border-radius: 16px;
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  border: 1.5px solid #e8f5e9;
  transition: all 0.25s;
  box-shadow: 0 2px 8px rgba(82, 196, 26, 0.06);
}

.company-card:hover {
  border-color: #52c41a;
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(82, 196, 26, 0.15);
}

.company-card-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.company-card h3 {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.company-card p {
  font-size: 13px;
  color: #888;
  line-height: 1.5;
  margin: 0;
}

.footer-section {
  text-align: center;
  padding: 40px;
  background: #1a1a2e;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}

@media (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .hero-title {
    font-size: 36px;
  }
  
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .hero-stats {
    flex-direction: column;
    gap: 20px;
  }
  
  .stat-divider {
    display: none;
  }
  
  .jobs-grid {
    grid-template-columns: 1fr;
  }
}
</style>
