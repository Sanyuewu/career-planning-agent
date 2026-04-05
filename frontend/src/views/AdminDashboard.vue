<template>
  <div class="admin-page">
    <div class="page-header">
      <div class="header-left">
        <h1>管理后台</h1>
        <p class="sub">系统运营数据概览与管理</p>
      </div>
      <div class="header-actions">
        <button class="action-btn" @click="exportData">
          <span>📥</span> 导出数据
        </button>
      </div>
    </div>

    <div class="stats-grid" v-if="stats">
      <div class="stat-card blue">
        <div class="stat-icon">👥</div>
        <div class="stat-body">
          <div class="stat-val">{{ stats.total_users }}</div>
          <div class="stat-label">注册用户</div>
          <div class="stat-trend up" v-if="stats.new_users_today">
            <span>↑</span> 今日+{{ stats.new_users_today }}
          </div>
        </div>
      </div>
      <div class="stat-card green">
        <div class="stat-icon">🎓</div>
        <div class="stat-body">
          <div class="stat-val">{{ stats.student_count }}</div>
          <div class="stat-label">学生用户</div>
        </div>
      </div>
      <div class="stat-card orange">
        <div class="stat-icon">🏢</div>
        <div class="stat-body">
          <div class="stat-val">{{ stats.company_count }}</div>
          <div class="stat-label">企业用户</div>
        </div>
      </div>
      <div class="stat-card purple">
        <div class="stat-icon">🎯</div>
        <div class="stat-body">
          <div class="stat-val">{{ stats.match_count }}</div>
          <div class="stat-label">匹配次数</div>
          <div class="stat-trend up" v-if="stats.matches_today">
            <span>↑</span> 今日+{{ stats.matches_today }}
          </div>
        </div>
      </div>
      <div class="stat-card teal">
        <div class="stat-icon">📊</div>
        <div class="stat-body">
          <div class="stat-val">{{ stats.report_count }}</div>
          <div class="stat-label">生成报告</div>
        </div>
      </div>
    </div>

    <div class="main-tabs">
      <button :class="['tab', { active: activeTab === 'overview' }]" @click="activeTab = 'overview'">数据概览</button>
      <button :class="['tab', { active: activeTab === 'users' }]" @click="activeTab = 'users'">用户管理</button>
      <button :class="['tab', { active: activeTab === 'jobs' }]" @click="activeTab = 'jobs'">岗位管理</button>
      <button :class="['tab', { active: activeTab === 'logs' }]" @click="activeTab = 'logs'">系统日志</button>
    </div>

    <div class="tab-content">
      <div v-if="activeTab === 'overview'" class="overview-panel">
        <div class="charts-row">
          <div class="chart-card">
            <div class="card-title">热门岗位 TOP10</div>
            <div ref="hotJobsChartRef" class="chart-area"></div>
          </div>
          <div class="chart-card">
            <div class="card-title">用户增长趋势</div>
            <div ref="userTrendChartRef" class="chart-area"></div>
          </div>
        </div>
        
        <div class="charts-row">
          <div class="chart-card">
            <div class="card-title">匹配热度分布</div>
            <div ref="matchDistChartRef" class="chart-area"></div>
          </div>
          <div class="chart-card">
            <div class="card-title">行业分布</div>
            <div ref="industryChartRef" class="chart-area"></div>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'users'" class="users-panel">
        <div class="panel-header">
          <div class="search-box">
            <input v-model="userSearch" placeholder="搜索用户名..." @input="searchUsers" />
          </div>
          <div class="filter-btns">
            <button
              v-for="f in roleFilters"
              :key="f.value"
              :class="['filter-btn', { active: roleFilter === f.value }]"
              @click="setRoleFilter(f.value)"
            >{{ f.label }}</button>
          </div>
        </div>

        <div class="user-table">
          <div class="table-head">
            <span>用户名</span>
            <span>角色</span>
            <span>关联ID</span>
            <span>注册时间</span>
            <span>最后活跃</span>
            <span>操作</span>
          </div>
          <div class="table-body">
            <div class="table-row" v-for="u in users" :key="u.username">
              <span class="uname">{{ u.username }}</span>
              <span>
                <span class="role-badge" :class="'role-' + u.role">{{ roleText(u.role) }}</span>
              </span>
              <span class="uid">{{ u.student_id || u.company_id || '-' }}</span>
              <span class="udate">{{ formatDate(u.created_at) }}</span>
              <span class="udate">{{ formatDate(u.last_active || '') }}</span>
              <span class="actions">
                <select class="role-select" :value="u.role" @change="changeRole(u.username, ($event.target as HTMLSelectElement).value)">
                  <option value="student">学生</option>
                  <option value="company">企业</option>
                  <option value="admin">管理员</option>
                </select>
                <button class="btn-text danger" @click="deleteUser(u.username)">删除</button>
              </span>
            </div>
          </div>
        </div>

        <div class="pagination">
          <button :disabled="page <= 1" @click="page--; loadUsers()">上一页</button>
          <span>第 {{ page }} 页 / 共 {{ totalPages }} 页</span>
          <button :disabled="page >= totalPages" @click="page++; loadUsers()">下一页</button>
        </div>
      </div>

      <div v-else-if="activeTab === 'jobs'" class="jobs-panel">
        <div class="panel-header">
          <h3>岗位数据管理</h3>
          <button class="action-btn" @click="refreshJobGraph">
            <span>🔄</span> 刷新图谱
          </button>
        </div>
        
        <div class="job-stats-grid">
          <div class="job-stat-card">
            <div class="stat-num">{{ jobStats.total_jobs }}</div>
            <div class="stat-desc">岗位总数</div>
          </div>
          <div class="job-stat-card">
            <div class="stat-num">{{ jobStats.total_skills }}</div>
            <div class="stat-desc">技能节点</div>
          </div>
          <div class="job-stat-card">
            <div class="stat-num">{{ jobStats.promotion_edges }}</div>
            <div class="stat-desc">晋升路径</div>
          </div>
          <div class="job-stat-card">
            <div class="stat-num">{{ jobStats.transfer_edges }}</div>
            <div class="stat-desc">换岗路径</div>
          </div>
        </div>

        <div class="jobs-table">
          <div class="table-head">
            <span>岗位名称</span>
            <span>所属行业</span>
            <span>技能数</span>
            <span>晋升目标</span>
            <span>换岗方向</span>
          </div>
          <div class="table-body">
            <div class="table-row" v-for="job in jobList" :key="job.title">
              <span class="job-title">{{ job.title }}</span>
              <span>{{ job.industry || '-' }}</span>
              <span>{{ job.skill_count || 0 }}</span>
              <span>{{ job.promotion_count || 0 }}</span>
              <span>{{ job.transfer_count || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'logs'" class="logs-panel">
        <div class="panel-header">
          <h3>系统日志</h3>
          <div class="filter-btns">
            <button
              v-for="l in logLevels"
              :key="l.value"
              :class="['filter-btn', { active: logLevel === l.value }]"
              @click="setLogLevel(l.value)"
            >{{ l.label }}</button>
          </div>
        </div>
        
        <div class="logs-list">
          <div class="log-item" v-for="(log, i) in logs" :key="i" :class="'level-' + log.level">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-level">{{ log.level.toUpperCase() }}</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { request } from '../api/http'
import { Message, Modal } from '@arco-design/web-vue'
import * as echarts from 'echarts'
import { ROLE_FILTER_OPTIONS, LOG_LEVEL_OPTIONS } from '../constants'

interface Stats {
  total_users: number
  student_count: number
  company_count: number
  admin_count: number
  match_count: number
  report_count: number
  new_users_today?: number
  matches_today?: number
}

interface UserRow {
  username: string
  role: string
  student_id: string
  company_id?: string
  created_at: string
  last_active?: string
}

interface JobStats {
  total_jobs: number
  total_skills: number
  promotion_edges: number
  transfer_edges: number
}

interface JobRow {
  title: string
  industry?: string
  skill_count: number
  promotion_count: number
  transfer_count: number
}

interface LogItem {
  time: string
  level: string
  message: string
}

const activeTab = ref('overview')
const stats = ref<Stats | null>(null)
const users = ref<UserRow[]>([])
const page = ref(1)
const pageSize = 15
const totalCount = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))
const roleFilter = ref('')
const userSearch = ref('')

const jobStats = ref<JobStats>({ total_jobs: 0, total_skills: 0, promotion_edges: 0, transfer_edges: 0 })
const jobList = ref<JobRow[]>([])

const logs = ref<LogItem[]>([])
const logLevel = ref('')

const hotJobsChartRef = ref<HTMLElement | null>(null)
const userTrendChartRef = ref<HTMLElement | null>(null)
const matchDistChartRef = ref<HTMLElement | null>(null)
const industryChartRef = ref<HTMLElement | null>(null)

let hotJobsChart: echarts.ECharts | null = null
let userTrendChart: echarts.ECharts | null = null
let matchDistChart: echarts.ECharts | null = null
let industryChart: echarts.ECharts | null = null

const chartObservers: ResizeObserver[] = []
function watchChartResize(containerRef: HTMLElement | null, chart: () => echarts.ECharts | null) {
  if (!containerRef) return
  const obs = new ResizeObserver(() => chart()?.resize())
  obs.observe(containerRef)
  chartObservers.push(obs)
}

const roleFilters = ROLE_FILTER_OPTIONS
const logLevels = LOG_LEVEL_OPTIONS

function roleText(r: string) {
  return { student: '学生', company: '企业', admin: '管理员' }[r] || r
}

function formatDate(d: string) {
  return d ? d.slice(0, 10) : '-'
}

async function loadStats() {
  try {
    stats.value = await request.get<Stats>('/admin/stats')
  } catch (e) {
    // silent
  }
}

async function loadUsers() {
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize) })
    if (roleFilter.value) params.append('role_filter', roleFilter.value)
    if (userSearch.value) params.append('search', userSearch.value)
    const res = await request.get<{ total: number; users: UserRow[] }>(`/admin/users?${params}`)
    users.value = res.users || []
    totalCount.value = res.total || 0
  } catch (e) {
    users.value = []
  }
}

async function loadJobStats() {
  try {
    const res = await request.get<JobStats & { jobs: JobRow[] }>('/admin/job_stats')
    jobStats.value = { total_jobs: res.total_jobs, total_skills: res.total_skills, promotion_edges: res.promotion_edges, transfer_edges: res.transfer_edges }
    jobList.value = res.jobs || []
  } catch (e) {
    // silent
  }
}

async function loadLogs() {
  try {
    const res = await request.get<LogItem[]>(`/admin/logs?level=${logLevel.value}`)
    logs.value = res
  } catch {
    logs.value = []
  }
}

async function loadHotJobsChart() {
  try {
    const res = await request.get<{ hot_jobs: { job_name: string; jd_count: number }[] }>('/admin/hot_jobs?limit=10')
    if (!hotJobsChartRef.value) return
    if (!hotJobsChart) {
      hotJobsChart = echarts.init(hotJobsChartRef.value)
      watchChartResize(hotJobsChartRef.value, () => hotJobsChart)
    }
    
    const jobs = (res.hot_jobs || []).slice().reverse()
    hotJobsChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 100, right: 20, top: 10, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: jobs.map(j => j.job_name), axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar',
        data: jobs.map(j => j.jd_count),
        itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#667eea' }, { offset: 1, color: '#764ba2' }] } },
        barMaxWidth: 20,
        label: { show: true, position: 'right', fontSize: 11 },
      }],
    })
  } catch {}
}

async function loadUserTrendChart() {
  if (!userTrendChartRef.value) return
  if (!userTrendChart) {
    userTrendChart = echarts.init(userTrendChartRef.value)
    watchChartResize(userTrendChartRef.value, () => userTrendChart)
  }
  try {
    const res = await request.get<{ dates: string[]; new_users: number[]; active_users: number[] }>('/admin/user_trends')
    userTrendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0, data: ['新增用户', '活跃用户'] },
      grid: { left: 40, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: res.dates },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        { name: '新增用户', type: 'line', smooth: true, data: res.new_users, areaStyle: { opacity: 0.3 }, lineStyle: { color: '#667eea' }, itemStyle: { color: '#667eea' } },
        { name: '活跃用户', type: 'line', smooth: true, data: res.active_users, areaStyle: { opacity: 0.3 }, lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      ],
    })
  } catch {
    userTrendChart.setOption({ graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fill: '#aaa', fontSize: 14 } }] })
  }
}

async function loadMatchDistChart() {
  if (!matchDistChartRef.value) return
  if (!matchDistChart) {
    matchDistChart = echarts.init(matchDistChartRef.value)
    watchChartResize(matchDistChartRef.value, () => matchDistChart)
  }
  try {
    const res = await request.get<{ ranges: string[]; counts: number[] }>('/admin/match_distribution')
    const total = res.counts.reduce((a, b) => a + b, 0)
    const colors = ['#52c41a', '#faad14', '#ff4d4f']
    const data = res.ranges.map((name, i) => ({ value: res.counts[i], name, itemStyle: { color: colors[i] } }))
    matchDistChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: total > 0 ? data : [{ value: 1, name: '暂无数据', itemStyle: { color: '#eee' } }],
        label: { show: true, formatter: total > 0 ? '{b}: {d}%' : '{b}' },
      }],
    })
  } catch {
    matchDistChart.setOption({ graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fill: '#aaa', fontSize: 14 } }] })
  }
}

async function loadIndustryChart() {
  if (!industryChartRef.value) return
  if (!industryChart) {
    industryChart = echarts.init(industryChartRef.value)
    watchChartResize(industryChartRef.value, () => industryChart)
  }
  try {
    const res = await request.get<{ jobs: string[]; counts: number[] }>('/admin/industry_stats')
    const jobs = [...res.jobs].reverse()
    const counts = [...res.counts].reverse()
    industryChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 120, right: 30, top: 10, bottom: 20 },
      xAxis: { type: 'value', minInterval: 1 },
      yAxis: { type: 'category', data: jobs.length ? jobs : ['暂无数据'], axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar',
        data: counts.length ? counts : [0],
        itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#667eea' }, { offset: 1, color: '#764ba2' }] } },
        barMaxWidth: 18,
        label: { show: true, position: 'right', fontSize: 11 },
      }],
    })
  } catch {
    industryChart.setOption({ graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: '暂无数据', fill: '#aaa', fontSize: 14 } }] })
  }
}

async function changeRole(username: string, newRole: string) {
  try {
    await request.put(`/admin/users/${username}/role`, { role: newRole })
    Message.success('角色已更新')
    await loadUsers()
  } catch (e: any) {
    Message.error(e?.message || '修改失败')
  }
}

async function deleteUser(username: string) {
  Modal.confirm({
    title: '确认删除',
    content: `确定删除用户 ${username}？此操作不可恢复。`,
    okText: '确认删除',
    cancelText: '取消',
    okButtonProps: { status: 'danger' },
    onOk: async () => {
      try {
        await request.delete(`/admin/users/${username}`)
        Message.success('已删除')
        loadUsers()
      } catch (e: any) {
        Message.error(e?.message || '删除失败')
      }
    }
  })
}

function setRoleFilter(val: string) {
  roleFilter.value = val
  page.value = 1
  loadUsers()
}

function searchUsers() {
  page.value = 1
  loadUsers()
}

function setLogLevel(val: string) {
  logLevel.value = val
  loadLogs()
}

async function refreshJobGraph() {
  try {
    await request.post('/admin/refresh_job_graph')
    Message.success('图谱已刷新')
    loadJobStats()
  } catch (e: any) {
    Message.error(e?.message || '刷新失败')
  }
}

function exportData() {
  Message.info('数据导出功能开发中...')
}

watch(activeTab, (tab) => {
  if (tab === 'overview') {
    setTimeout(() => {
      loadHotJobsChart()
      loadUserTrendChart()
      loadMatchDistChart()
      loadIndustryChart()
    }, 100)
  }
})

onMounted(async () => {
  await Promise.all([loadStats(), loadUsers(), loadJobStats()])
  loadHotJobsChart()
  loadUserTrendChart()
  loadMatchDistChart()
  loadIndustryChart()
})

onUnmounted(() => {
  chartObservers.forEach(o => o.disconnect())
  chartObservers.length = 0
  hotJobsChart?.dispose()
  userTrendChart?.dispose()
  matchDistChart?.dispose()
  industryChart?.dispose()
  hotJobsChart = null
  userTrendChart = null
  matchDistChart = null
  industryChart = null
})
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 80px 40px 40px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px;
}

.sub {
  font-size: 14px;
  color: #888;
  margin: 0;
}

.action-btn {
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  background: white;
  border: 1px solid #e5e5e5;
  color: #333;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-card.blue .stat-icon { background: #e8f4ff; }
.stat-card.green .stat-icon { background: #f0ffe8; }
.stat-card.orange .stat-icon { background: #fff7e6; }
.stat-card.purple .stat-icon { background: #f5f0ff; }
.stat-card.teal .stat-icon { background: #e6fffb; }

.stat-val {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-label {
  font-size: 12px;
  color: #888;
}

.stat-trend {
  font-size: 11px;
  margin-top: 4px;
}

.stat-trend.up { color: #52c41a; }
.stat-trend.down { color: #ff4d4f; }

.main-tabs {
  display: flex;
  gap: 4px;
  background: white;
  padding: 6px;
  border-radius: 12px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.tab {
  padding: 10px 24px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.tab:hover { background: #f5f5f5; }

.tab.active {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.tab-content {
  min-height: 500px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.chart-area {
  height: 280px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.search-box input {
  padding: 10px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  width: 240px;
}

.search-box input:focus {
  border-color: #667eea;
}

.filter-btns {
  display: flex;
  gap: 6px;
}

.filter-btn {
  padding: 6px 14px;
  border: 1.5px solid #e0e0e0;
  border-radius: 8px;
  background: none;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn.active {
  border-color: #667eea;
  color: #667eea;
  background: #f0f4ff;
}

.user-table, .jobs-table {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.table-head, .table-row {
  display: grid;
  grid-template-columns: 1.5fr 0.8fr 1fr 1fr 1fr 1.2fr;
  gap: 8px;
  padding: 12px 16px;
  align-items: center;
}

.table-head {
  font-weight: 600;
  color: #888;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
  background: #fafafa;
}

.table-row {
  border-bottom: 1px solid #fafafa;
  font-size: 13px;
}

.table-row:hover { background: #f8f8ff; }

.uname, .job-title { font-weight: 500; color: #333; }
.uid, .udate { color: #aaa; font-size: 12px; }

.role-badge {
  padding: 3px 10px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}

.role-student { background: #e8f4ff; color: #1890ff; }
.role-company { background: #f0ffe8; color: #52c41a; }
.role-admin { background: #fff7e6; color: #fa8c16; }

.role-select {
  border: 1.5px solid #e0e0e0;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  color: #555;
  cursor: pointer;
  background: #fff;
}

.actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-text {
  background: none;
  border: none;
  color: #667eea;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 8px;
}

.btn-text.danger { color: #ff4d4f; }
.btn-text:hover { text-decoration: underline; }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 20px;
  font-size: 13px;
  color: #666;
}

.pagination button {
  padding: 6px 16px;
  border: 1.5px solid #e0e0e0;
  border-radius: 8px;
  background: none;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.pagination button:not(:disabled):hover { border-color: #667eea; color: #667eea; }

.job-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.job-stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.job-stat-card .stat-num {
  font-size: 32px;
  font-weight: 700;
  color: #667eea;
}

.job-stat-card .stat-desc {
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}

.logs-list {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
  font-family: monospace;
}

.log-item:last-child { border-bottom: none; }

.log-time { color: #999; width: 160px; flex-shrink: 0; }
.log-level { width: 50px; font-weight: 600; }
.log-msg { flex: 1; color: #333; }

.log-item.level-error .log-level { color: #ff4d4f; }
.log-item.level-warn .log-level { color: #faad14; }
.log-item.level-info .log-level { color: #1890ff; }

@media (max-width: 1200px) {
  .stats-grid { grid-template-columns: repeat(3, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .admin-page { padding: 70px 16px 24px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .job-stats-grid { grid-template-columns: repeat(2, 1fr); }
  .table-head, .table-row { grid-template-columns: 1fr 0.8fr 1fr; }
  .table-head span:nth-child(n+4), .table-row span:nth-child(n+4) { display: none; }
}
</style>
