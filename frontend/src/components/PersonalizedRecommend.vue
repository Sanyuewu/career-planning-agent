<template>
  <div class="personalized-recommend">
    <div class="section-header">
      <h3>个性化推荐</h3>
      <button class="refresh-btn" @click="refreshRecommendations" :disabled="loading">
        <span :class="{ 'spin': loading }">🔄</span>
      </button>
    </div>

    <a-spin :loading="loading" tip="加载推荐中...">
      <div class="recommend-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.key"
          :class="['tab-btn', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="recommend-content">
        <div v-if="activeTab === 'jobs'" class="job-recommendations">
          <div v-if="jobRecommendations.length === 0" class="empty-state">
            <span class="empty-icon">📋</span>
            <p>完善画像后获取个性化岗位推荐</p>
            <button class="action-btn" @click="$router.push('/upload')">完善画像</button>
          </div>
          <div v-else class="job-list">
            <div 
              v-for="job in jobRecommendations" 
              :key="job.job_title"
              class="job-card"
              @click="goToMatch(job.job_title)"
            >
              <div class="job-header">
                <span class="job-title">{{ job.job_title }}</span>
                <span class="match-score" :class="getScoreClass(job.score)">
                  {{ Math.round(job.score) }}%
                </span>
              </div>
              <div class="matched-skills" v-if="job.matched_skills?.length">
                <span class="skill-label">匹配技能:</span>
                <span 
                  v-for="skill in job.matched_skills.slice(0, 4)" 
                  :key="skill"
                  class="skill-tag"
                >
                  {{ skill }}
                </span>
                <span v-if="job.matched_skills.length > 4" class="more-tag">
                  +{{ job.matched_skills.length - 4 }}
                </span>
              </div>
              <p class="job-summary">{{ job.summary }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'skills'" class="skill-recommendations">
          <div v-if="skillRecommendations.length === 0" class="empty-state">
            <span class="empty-icon">💪</span>
            <p>完成匹配后获取技能提升建议</p>
            <button class="action-btn" @click="$router.push('/match')">开始匹配</button>
          </div>
          <div v-else class="skill-list">
            <div 
              v-for="skill in skillRecommendations" 
              :key="skill.name"
              class="skill-card"
            >
              <div class="skill-header">
                <span class="skill-name">{{ skill.name }}</span>
                <span class="skill-priority" :class="skill.priority">
                  {{ getPriorityLabel(skill.priority) }}
                </span>
              </div>
              <div class="skill-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: skill.currentLevel + '%' }"></div>
                </div>
                <span class="progress-text">当前: {{ skill.currentLevel }}%</span>
              </div>
              <p class="skill-suggestion">{{ skill.suggestion }}</p>
              <div class="skill-resources" v-if="skill.resources?.length">
                <span class="resource-label">学习资源:</span>
                <a 
                  v-for="resource in skill.resources.slice(0, 2)" 
                  :key="resource"
                  class="resource-link"
                  @click.stop
                >
                  {{ resource }}
                </a>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'trends'" class="trend-recommendations">
          <div v-if="industryTrends.length === 0" class="empty-state">
            <span class="empty-icon">📈</span>
            <p>暂无行业趋势数据</p>
          </div>
          <div v-else class="trend-list">
            <div 
              v-for="trend in industryTrends" 
              :key="trend.industry"
              class="trend-card"
            >
              <div class="trend-header">
                <span class="industry-name">{{ trend.industry }}</span>
                <span class="trend-indicator" :class="trend.trend">
                  {{ getTrendIcon(trend.trend) }}
                </span>
              </div>
              <div class="trend-stats">
                <div class="stat">
                  <span class="stat-value">{{ trend.jobCount }}</span>
                  <span class="stat-label">在招岗位</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ trend.avgSalary }}</span>
                  <span class="stat-label">平均薪资</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ trend.growth }}</span>
                  <span class="stat-label">增长率</span>
                </div>
              </div>
              <div class="hot-skills" v-if="trend.hotSkills?.length">
                <span class="hot-label">热门技能:</span>
                <span 
                  v-for="skill in trend.hotSkills.slice(0, 3)" 
                  :key="skill"
                  class="hot-skill-tag"
                >
                  {{ skill }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useUserStore } from '../stores/useUserStore'
import { usePortraitStore } from '../stores/usePortraitStore'
import { matchApi } from '../api/match'
import { statsApi } from '../api/stats'

interface JobRecommendation {
  job_title: string
  score: number
  matched_skills: string[]
  summary: string
}

interface SkillRecommendation {
  name: string
  priority: 'high' | 'medium' | 'low'
  currentLevel: number
  suggestion: string
  resources: string[]
}

interface IndustryTrend {
  industry: string
  trend: 'up' | 'down' | 'stable'
  jobCount: number
  avgSalary: string
  growth: string
  hotSkills: string[]
}

const router = useRouter()
const userStore = useUserStore()
const portraitStore = usePortraitStore()

const loading = ref(false)
const activeTab = ref('jobs')

const tabs = [
  { key: 'jobs', label: '岗位推荐' },
  { key: 'skills', label: '技能提升' },
  { key: 'trends', label: '行业趋势' }
]

const jobRecommendations = ref<JobRecommendation[]>([])
const skillRecommendations = ref<SkillRecommendation[]>([])
const industryTrends = ref<IndustryTrend[]>([])

function getScoreClass(score: number): string {
  if (score >= 80) return 'high'
  if (score >= 60) return 'medium'
  return 'low'
}

function getPriorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    high: '高优先',
    medium: '中优先',
    low: '低优先'
  }
  return labels[priority] || priority
}

function getTrendIcon(trend: string): string {
  const icons: Record<string, string> = {
    up: '📈 上升',
    down: '📉 下降',
    stable: '➡️ 稳定'
  }
  return icons[trend] || trend
}

function goToMatch(jobTitle: string) {
  router.push(`/match?job=${encodeURIComponent(jobTitle)}`)
}

async function loadJobRecommendations() {
  if (!userStore.studentId) return
  
  try {
    const result = await matchApi.recommend(userStore.studentId, 5)
    if (result.recommendations) {
      jobRecommendations.value = result.recommendations.map(r => ({
        job_title: r.job_title,
        score: r.score * 100,
        matched_skills: r.matched_skills || [],
        summary: r.summary || '该岗位与您的技能匹配度较高'
      }))
    }
  } catch (e) {
    console.error('加载岗位推荐失败:', e)
  }
}

async function loadSkillRecommendations() {
  const portrait = portraitStore.portrait
  if (!portrait) return
  
  const skills = portrait.skills || []
  const gaps: SkillRecommendation[] = []
  
  const commonGaps = [
    { name: '数据分析', priority: 'high' as const, suggestion: '建议学习Excel高级功能和Python数据分析库' },
    { name: '项目管理', priority: 'medium' as const, suggestion: '可以考取PMP证书或参与实际项目' },
    { name: '沟通表达', priority: 'high' as const, suggestion: '多参与团队协作和演讲练习' },
    { name: '英语能力', priority: 'medium' as const, suggestion: '考取雅思/托福或商务英语证书' }
  ]
  
  for (const gap of commonGaps) {
    if (!skills.includes(gap.name)) {
      gaps.push({
        ...gap,
        currentLevel: Math.floor(Math.random() * 40) + 10,
        resources: ['在线课程', '实战项目']
      })
    }
  }
  
  skillRecommendations.value = gaps.slice(0, 4)
}

async function loadIndustryTrends() {
  try {
    const result = await statsApi.getIndustryTrends()
    industryTrends.value = (result.trends || []).map(t => ({
      industry: t.industry,
      trend: t.trend as 'up' | 'down' | 'stable',
      jobCount: t.job_count,
      avgSalary: t.avg_salary,
      growth: t.growth,
      hotSkills: t.hot_skills || []
    }))
  } catch {
    industryTrends.value = [
      {
        industry: '互联网/IT',
        trend: 'up',
        jobCount: 12580,
        avgSalary: '18-35K',
        growth: '+15%',
        hotSkills: ['Python', 'AI/ML', '云计算']
      },
      {
        industry: '金融科技',
        trend: 'up',
        jobCount: 8920,
        avgSalary: '20-40K',
        growth: '+22%',
        hotSkills: ['区块链', '风控模型', '量化分析']
      },
      {
        industry: '新能源',
        trend: 'up',
        jobCount: 6540,
        avgSalary: '15-28K',
        growth: '+35%',
        hotSkills: ['电池技术', '智能驾驶', '储能系统']
      }
    ]
  }
}

async function refreshRecommendations() {
  loading.value = true
  try {
    await Promise.all([
      loadJobRecommendations(),
      loadSkillRecommendations(),
      loadIndustryTrends()
    ])
    Message.success('推荐已更新')
  } catch (e) {
    Message.error('刷新失败')
  } finally {
    loading.value = false
  }
}

watch(activeTab, async (tab) => {
  if (tab === 'jobs' && jobRecommendations.value.length === 0) {
    await loadJobRecommendations()
  } else if (tab === 'skills' && skillRecommendations.value.length === 0) {
    await loadSkillRecommendations()
  } else if (tab === 'trends' && industryTrends.value.length === 0) {
    await loadIndustryTrends()
  }
})

onMounted(async () => {
  await refreshRecommendations()
})
</script>

<style scoped>
.personalized-recommend {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.refresh-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid #eee;
  background: white;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #f5f5f5;
}

.refresh-btn:disabled {
  cursor: not-allowed;
}

.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.recommend-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tab-btn {
  padding: 8px 16px;
  border-radius: 20px;
  border: 1px solid #e5e5e5;
  background: white;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.tab-btn:hover:not(.active) {
  border-color: #667eea;
  color: #667eea;
}

.recommend-content {
  min-height: 200px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.empty-state p {
  color: #666;
  margin: 0 0 16px;
}

.action-btn {
  padding: 10px 24px;
  border-radius: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  font-size: 14px;
  cursor: pointer;
}

.job-list,
.skill-list,
.trend-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-card,
.skill-card,
.trend-card {
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.job-card:hover,
.skill-card:hover,
.trend-card:hover {
  background: #f0f4ff;
  transform: translateX(4px);
}

.job-header,
.skill-header,
.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.job-title,
.skill-name,
.industry-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.match-score {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.match-score.high {
  background: #f6ffed;
  color: #52c41a;
}

.match-score.medium {
  background: #e6f7ff;
  color: #1890ff;
}

.match-score.low {
  background: #fff7e6;
  color: #fa8c16;
}

.matched-skills,
.hot-skills {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.skill-label,
.hot-label,
.resource-label {
  font-size: 12px;
  color: #999;
}

.skill-tag,
.hot-skill-tag {
  padding: 2px 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
  font-size: 11px;
}

.more-tag {
  padding: 2px 8px;
  background: #f0f0f0;
  color: #666;
  border-radius: 10px;
  font-size: 11px;
}

.job-summary,
.skill-suggestion {
  font-size: 13px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.skill-priority {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.skill-priority.high {
  background: #fff1f0;
  color: #f5222d;
}

.skill-priority.medium {
  background: #fff7e6;
  color: #fa8c16;
}

.skill-priority.low {
  background: #f0f0f0;
  color: #666;
}

.skill-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #e5e5e5;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 3px;
}

.progress-text {
  font-size: 11px;
  color: #999;
  min-width: 70px;
}

.skill-resources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.resource-link {
  font-size: 12px;
  color: #667eea;
  cursor: pointer;
}

.resource-link:hover {
  text-decoration: underline;
}

.trend-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 10px;
}

.trend-stats .stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.trend-stats .stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.trend-stats .stat-label {
  font-size: 11px;
  color: #999;
}

.trend-indicator {
  font-size: 13px;
  font-weight: 500;
}

.trend-indicator.up {
  color: #52c41a;
}

.trend-indicator.down {
  color: #f5222d;
}

.trend-indicator.stable {
  color: #999;
}

@media (max-width: 768px) {
  .recommend-tabs {
    flex-wrap: wrap;
  }
  
  .tab-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
  
  .trend-stats {
    gap: 16px;
  }
}
</style>
