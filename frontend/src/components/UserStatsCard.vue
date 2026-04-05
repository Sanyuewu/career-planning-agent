<template>
  <div class="user-stats-card">
    <div class="stats-header">
      <div class="user-info" v-if="userStore.isLoggedIn">
        <div class="avatar">{{ avatarInitial }}</div>
        <div class="user-detail">
          <h3>{{ userStore.studentName || '用户' }}</h3>
          <span class="user-role">{{ roleLabel }}</span>
        </div>
      </div>
      <div class="user-info guest" v-else>
        <div class="avatar guest-avatar">游</div>
        <div class="user-detail">
          <h3>游客模式</h3>
          <span class="login-hint" @click="$router.push('/login')">点击登录</span>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-item">
        <div class="stat-circle" :style="{ background: completenessGradient }">
          <span class="stat-value">{{ Math.round(stats.portraitCompleteness) }}</span>
          <span class="stat-unit">%</span>
        </div>
        <span class="stat-label">画像完整度</span>
      </div>

      <div class="stat-item">
        <div class="stat-number">
          <span class="number">{{ stats.matchCount }}</span>
          <span class="unit">次</span>
        </div>
        <span class="stat-label">人岗匹配</span>
      </div>

      <div class="stat-item">
        <div class="stat-number">
          <span class="number">{{ stats.reportCount }}</span>
          <span class="unit">份</span>
        </div>
        <span class="stat-label">职业报告</span>
      </div>

      <div class="stat-item">
        <div class="stat-number">
          <span class="number">{{ stats.chatSessionCount }}</span>
          <span class="unit">次</span>
        </div>
        <span class="stat-label">AI对话</span>
      </div>
    </div>

    <div class="achievements" v-if="stats.achievements?.length">
      <h4>成就徽章</h4>
      <div class="achievement-list">
        <div 
          v-for="achievement in stats.achievements" 
          :key="achievement"
          class="achievement-badge"
          :title="getAchievementTitle(achievement)"
        >
          {{ getAchievementIcon(achievement) }}
        </div>
      </div>
    </div>

    <div class="last-active" v-if="stats.lastActiveAt">
      <span class="time-icon">🕐</span>
      <span>最近活跃: {{ formatLastActive(stats.lastActiveAt) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import { usePortraitStore } from '../stores/usePortraitStore'
import { useMatchStore } from '../stores/useMatchStore'
import { statsApi, type AchievementItem } from '../api/stats'

interface UserStats {
  portraitCompleteness: number
  matchCount: number
  reportCount: number
  chatSessionCount: number
  lastActiveAt: string
  achievements: string[]
  activityTrend: Array<{ date: string; matches: number; reports: number }>
  skillProgress: Record<string, { current: number; target: number }>
}

interface AchievementDisplay extends AchievementItem {
  unlocked: boolean
}

const userStore = useUserStore()
const portraitStore = usePortraitStore()
const matchStore = useMatchStore()

const stats = ref<UserStats>({
  portraitCompleteness: 0,
  matchCount: 0,
  reportCount: 0,
  chatSessionCount: 0,
  lastActiveAt: '',
  achievements: [],
  activityTrend: [],
  skillProgress: {}
})

const achievementDetails = ref<AchievementDisplay[]>([])

const avatarInitial = computed(() => {
  const name = userStore.studentName
  return name ? name.charAt(0).toUpperCase() : 'U'
})

const roleLabel = computed(() => {
  const role = userStore.role
  if (role === 'student') return '学生用户'
  if (role === 'company') return '企业用户'
  if (role === 'admin') return '管理员'
  return '用户'
})

const completenessGradient = computed(() => {
  const completeness = stats.value.portraitCompleteness
  if (completeness >= 80) {
    return 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)'
  } else if (completeness >= 50) {
    return 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)'
  } else {
    return 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)'
  }
})

function getAchievementIcon(achievement: string): string {
  const icons: Record<string, string> = {
    'first_match': '🎯',
    'first_report': '📊',
    'complete_profile': '✨',
    'active_user': '🔥',
    'skill_master': '💪',
    'career_explorer': '🧭',
    'chat_master': '💬',
    'report_pro': '📄'
  }
  return icons[achievement] || '🏆'
}

function getAchievementTitle(achievement: string): string {
  const titles: Record<string, string> = {
    'first_match': '首次匹配',
    'first_report': '首份报告',
    'complete_profile': '画像完善',
    'active_user': '活跃用户',
    'skill_master': '技能达人',
    'career_explorer': '职业探索者',
    'chat_master': '对话达人',
    'report_pro': '报告专家'
  }
  return titles[achievement] || achievement
}

function formatLastActive(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

async function loadStats() {
  if (userStore.studentId) {
    try {
      const apiStats = await statsApi.getUserStats(userStore.studentId)
      stats.value = {
        portraitCompleteness: (apiStats.portrait_completeness || 0) * 100,
        matchCount: apiStats.match_count || 0,
        reportCount: apiStats.report_count || 0,
        chatSessionCount: apiStats.chat_session_count || 0,
        lastActiveAt: apiStats.last_active_at || '',
        achievements: apiStats.achievements || [],
        activityTrend: apiStats.activity_trend || [],
        skillProgress: apiStats.skill_progress || {}
      }
      
      const achievementsData = await statsApi.getAchievements(userStore.studentId)
      achievementDetails.value = (achievementsData.achievements || []).map(a => ({
        ...a,
        unlocked: a.unlocked_at !== null
      }))
    } catch (e) {
      console.error('加载统计数据失败，使用本地数据:', e)
      await portraitStore.loadPortrait()
      stats.value.portraitCompleteness = (portraitStore.portrait?.completeness || 0) * 100
      
      const history = matchStore.results || []
      stats.value.matchCount = history.length
      
      stats.value.lastActiveAt = localStorage.getItem('last_active_time') || ''
      
      const achievements: string[] = []
      if (stats.value.matchCount >= 1) achievements.push('first_match')
      if (stats.value.portraitCompleteness >= 80) achievements.push('complete_profile')
      if (stats.value.matchCount >= 5) achievements.push('active_user')
      stats.value.achievements = achievements
    }
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.user-stats-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.stats-header {
  margin-bottom: 24px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
}

.guest-avatar {
  background: #f0f0f0;
  color: #999;
}

.user-detail h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
}

.user-role {
  font-size: 13px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 10px;
  border-radius: 10px;
}

.login-hint {
  font-size: 13px;
  color: #667eea;
  cursor: pointer;
}

.login-hint:hover {
  text-decoration: underline;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
}

.stat-unit {
  font-size: 11px;
}

.stat-number {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.stat-number .number {
  font-size: 28px;
  font-weight: 700;
  color: #667eea;
}

.stat-number .unit {
  font-size: 12px;
  color: #999;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.achievements {
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  margin-bottom: 16px;
}

.achievements h4 {
  font-size: 13px;
  color: #666;
  margin: 0 0 12px;
}

.achievement-list {
  display: flex;
  gap: 8px;
}

.achievement-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f8f9ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  transition: transform 0.2s;
}

.achievement-badge:hover {
  transform: scale(1.1);
}

.last-active {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #999;
}

.time-icon {
  font-size: 14px;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .stat-circle {
    width: 56px;
    height: 56px;
  }
  
  .stat-value {
    font-size: 18px;
  }
  
  .stat-number .number {
    font-size: 24px;
  }
}
</style>
