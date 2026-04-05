<template>
  <div class="graph-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">←</button>
      <div>
        <h1>职业图谱</h1>
        <p>职业发展路径可视化</p>
      </div>
    </div>
    
    <a-row :gutter="24">
      <a-col :span="18">
        <a-card class="graph-card">
          <template #title>
            <div class="card-header">
              <span>职业发展图谱</span>
              <a-input-search 
                v-model="searchQuery" 
                placeholder="搜索岗位名称" 
                style="width: 240px"
                :loading="searching"
                @search="searchJob" 
              />
            </div>
          </template>
          <!-- 首次使用引导提示 -->
          <div v-if="showHint" class="graph-hint">
            <span>💡 点击节点查看岗位详情，拖拽可重新布局，右侧搜索框可定位具体岗位</span>
            <button class="hint-close" @click="dismissHint">知道了</button>
          </div>
          <a-spin :loading="loading" tip="加载图谱数据...">
            <div ref="graphChartRef" class="graph-chart"></div>
          </a-spin>
        </a-card>
        
        <a-card class="timeline-card" v-if="currentJob">
          <template #title>
            <div class="card-header">
              <span>薪资成长曲线</span>
            </div>
          </template>
          <CareerTimeline :jobName="currentJob.title || currentJob.name || searchQuery" />
        </a-card>
      </a-col>
      
      <a-col :span="6">
        <a-card title="当前岗位" class="info-card" v-if="currentJob">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="岗位名称">{{ currentJob.title || currentJob.name }}</a-descriptions-item>
            <a-descriptions-item label="所属行业">{{ currentJob.industry || '-' }}</a-descriptions-item>
            <a-descriptions-item label="薪资范围">{{ currentJob.salary || '-' }}</a-descriptions-item>
          </a-descriptions>
          
          <a-divider />
          
          <h4>晋升路径</h4>
          <a-empty v-if="promotionPaths.length === 0" description="暂无晋升路径" />
          <a-steps direction="vertical" :current="-1" size="small" v-else>
            <a-step v-for="(path, idx) in promotionPaths" :key="`promo-${idx}`" :title="path.to">
              <template #description>
                <div class="step-desc">
                  <span v-if="path.years">年限: {{ path.years }}</span>
                  <span v-if="path.description">{{ path.description }}</span>
                </div>
              </template>
            </a-step>
          </a-steps>
          
          <a-divider />
          
          <h4>换岗路径</h4>
          <a-empty v-if="transferPaths.length === 0" description="暂无换岗路径" />
          <a-list :bordered="false" size="small" v-else>
            <a-list-item v-for="(path, idx) in transferPaths" :key="`transfer-${idx}`">
              <a-list-item-meta>
                <template #title>
                  <span>{{ path.target }}</span>
                  <a-tag :color="getMatchColor(path.matchLevel)" size="small" style="margin-left: 8px">
                    匹配度: {{ path.matchLevel }}
                  </a-tag>
                </template>
                <template #description>
                  <div v-if="path.advantage" class="transfer-desc">优势: {{ path.advantage }}</div>
                  <div v-if="path.needLearn" class="transfer-desc need-learn">需补足: {{ path.needLearn }}</div>
                </template>
              </a-list-item-meta>
            </a-list-item>
          </a-list>
        </a-card>
        
        <a-card v-else title="岗位信息" class="info-card">
          <a-empty description="点击图谱节点查看岗位详情" />
        </a-card>
        
        <a-card title="图例" class="legend-card">
          <div class="legend-item">
            <span class="legend-color promotion"></span>
            <span>晋升路径</span>
          </div>
          <div class="legend-item">
            <span class="legend-color transfer"></span>
            <span>换岗路径</span>
          </div>
          <div class="legend-item">
            <span class="legend-color similar"></span>
            <span>相似技能</span>
          </div>
        </a-card>
        
        <a-card title="热门岗位" class="hot-jobs-card">
          <a-spin :loading="loadingHotJobs">
            <div class="hot-job-list">
              <a-tag 
                v-for="job in hotJobs" 
                :key="job.id" 
                color="arcoblue" 
                style="margin: 4px; cursor: pointer"
                @click="selectJobByName(job.title)"
              >
                {{ job.title }}
              </a-tag>
            </div>
          </a-spin>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useECharts, createForceGraphOption } from '../composables/useECharts'
import { jobApi, type GraphPathData, type MainTransfers } from '../api/job'
import type { CareerGraphNode, JobInfo } from '../types/index'
import CareerTimeline from '../components/graph/CareerTimeline.vue'

const graphChartRef = ref<HTMLElement | null>(null)
const { setOption, on, showLoading, hideLoading } = useECharts(graphChartRef)

const searchQuery = ref('')
const searching = ref(false)
const loading = ref(false)

const showHint = ref(!localStorage.getItem('graph_hint_shown'))
function dismissHint() {
  showHint.value = false
  localStorage.setItem('graph_hint_shown', '1')
}
const loadingHotJobs = ref(false)
const currentJob = ref<CareerGraphNode | null>(null)
const promotionPaths = ref<Array<{ to: string; years?: string; description?: string }>>([])
const transferPaths = ref<Array<{ target: string; matchLevel: string; advantage?: string; needLearn?: string }>>([])
const hotJobs = ref<JobInfo[]>([])

const graphData = ref<GraphPathData | null>(null)

function getMatchColor(level: string): string {
  const colors: Record<string, string> = {
    '高': 'green',
    '中': 'orange',
    '低': 'red',
  }
  return colors[level] || 'gray'
}

async function loadHotJobs() {
  loadingHotJobs.value = true
  try {
    const jobs = await jobApi.getJobs()
    hotJobs.value = jobs.slice(0, 15).map((title, i) => ({ id: i.toString(), title }))
  } catch (error) {
  } finally {
    loadingHotJobs.value = false
  }
}

async function loadGraph(jobName: string) {
  loading.value = true
  showLoading()
  
  try {
    const urlParams = new URLSearchParams(window.location.search)
    const mode = urlParams.get('mode') || 'full'
    
    if (mode === 'minimal' || urlParams.get('job')) {
      const data = await jobApi.getMainTransfers(jobName)
      renderMinimalGraph(data)
      const graphPathData: GraphPathData = {
        nodes: data.graph.nodes.map((n: any) => ({ id: n.id, title: n.title || n.id.replace('job_', '') })),
        edges: data.graph.edges.map((e: any) => ({ from: e.from, to: e.to, type: e.type || 'CAN_TRANSFER_TO', label: e.label }))
      }
      selectJob({ id: jobName, title: data.main?.title || jobName }, graphPathData)
      Message.success(`换岗图谱已加载 (${data.transfers.length}个机会)`)
    } else {
      const data = await jobApi.getCareerGraph(jobName)
      graphData.value = data as GraphPathData
      
      if (data.nodes && data.nodes.length > 0) {
        renderGraph(data as GraphPathData)
        
        const currentNode = data.nodes.find((n: { id: string; title: string }) => n.id === jobName || n.id === `job_${jobName}`)
        if (currentNode) {
          selectJob(currentNode, data as GraphPathData)
        }
      } else {
        Message.warning('未找到该岗位的图谱数据')
        hideLoading()
      }
    }
  } catch (error: any) {
    Message.error(error?.message || '加载图谱数据失败')
    hideLoading()
  } finally {
    loading.value = false
  }
}

function renderGraph(data: GraphPathData) {
  const nodes = data.nodes.map(n => ({
    id: n.id,
    name: n.title || n.id.replace('job_', ''),
    category: getCategory(n.id, data),
  }))
  
  const edges = data.edges.map(e => ({
    source: e.from,
    target: e.to,
    value: e.type === 'PROMOTES_TO' ? 3 : e.label === '高' ? 2 : 1,
    lineStyle: {
      color: e.type === 'PROMOTES_TO' ? '#1890ff' : '#52c41a',
      width: e.type === 'PROMOTES_TO' ? 2 : 1,
      curveness: 0.1,
    },
  }))
  
  const categories = [
    { name: '当前岗位' },
    { name: '晋升方向' },
    { name: '换岗方向' },
  ]
  
  setOption(createForceGraphOption(nodes, edges, categories))
  hideLoading()
}

function renderMinimalGraph(data: MainTransfers) {
  // 最小模式：只渲染主节点 + 换岗子节点，突出展示换岗机会
  const nodes = data.graph.nodes.map(n => ({
    id: n.id,
    name: n.title || n.id.replace('job_', ''),
    category: 0,  // 主节点
  }))
  
  const edges = data.graph.edges.map(e => ({
    source: e.from,
    target: e.to,
    value: 4,  // 突出粗线
    lineStyle: {
      color: '#52c41a',  // 绿色换岗线
      width: 3,
      curveness: 0.3,
      type: 'dashed',  // 虚线更醒目
    },
    label: {
      show: true,
      formatter: e.label,
      position: 'end',
      color: '#52c41a',
    }
  }))
  
  const categories = [{ name: '主岗位 + 换岗机会' }]
  
  setOption(createForceGraphOption(nodes, edges, categories, {
    // 最小模式配置：固定布局，主节点居中
    layout: {
      type: 'circular',
      gravity: 0.1,
    }
  }))
}

function getCategory(nodeId: string, data: GraphPathData): number {
  const currentNodeId = currentJob.value?.id || ''
  if (nodeId === currentNodeId) return 0
  
  const isPromotion = data.edges.some(e => e.from === currentNodeId && e.to === nodeId && e.type === 'PROMOTES_TO')
  if (isPromotion) return 1
  
  const isTransfer = data.edges.some(e => e.from === currentNodeId && e.to === nodeId && e.type === 'CAN_TRANSFER_TO')
  if (isTransfer) return 2
  
  return 1
}

function selectJob(job: { id?: string; title?: string; name?: string; industry?: string; salary?: string } | null, data?: GraphPathData | MainTransfers | null) {
  if (!job) return
  const nodeId = job.id || job.name || ''
  
  const nodesArray = data && 'nodes' in data ? data.nodes : []
  const nodeInfo = nodesArray?.find((n: CareerGraphNode) => n.id === nodeId || n.title === job.title || n.id === `job_${job.title}`)
  
  const jobInfo: CareerGraphNode = {
    id: nodeId,
    title: job.title || job.name || nodeId.replace('job_', ''),
    industry: job.industry || nodeInfo?.industry || '-',
    salary: job.salary || nodeInfo?.salary || '-',
  }
  currentJob.value = jobInfo
  
  const graphDataToUse = data || graphData.value
  if (!graphDataToUse) return
  
  if ('edges' in graphDataToUse && Array.isArray(graphDataToUse.edges)) {
    promotionPaths.value = graphDataToUse.edges
      .filter((e: { from: string; to: string; type: string; label?: string }) => e.from === nodeId && e.type === 'PROMOTES_TO')
      .map((e: { from: string; to: string; type: string; label?: string }) => ({
        to: e.to.replace('job_', ''),
        years: e.label,
        description: '',
      }))
  }
  
  if ('promotion_paths' in graphDataToUse && graphDataToUse.promotion_paths && graphDataToUse.promotion_paths.length > 0) {
    const mainPath = graphDataToUse.promotion_paths[0] as { nodes?: unknown[]; transitions?: Array<{ to?: string; years?: string; description?: string }> }
    if (mainPath && mainPath.transitions) {
      promotionPaths.value = mainPath.transitions.map((t) => ({
        to: t.to?.replace('job_', '') || '',
        years: t.years,
        description: t.description,
      }))
    }
  }
  
  if ('transfer_paths' in graphDataToUse && graphDataToUse.transfer_paths) {
    transferPaths.value = (graphDataToUse.transfer_paths as Array<{ target: string; match_level?: string; advantage?: string; need_learn?: string }>)
      .filter(tp => tp.target)
      .map(tp => ({
        target: tp.target.replace('job_', ''),
        matchLevel: tp.match_level || '中',
        advantage: tp.advantage,
        needLearn: tp.need_learn,
      }))
  }
}

async function selectJobByName(jobName: string) {
  if (!jobName) return
  searchQuery.value = jobName
  await loadGraph(jobName)
}

// 防抖：用户停止输入 400ms 后才触发搜索建议加载
let _debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, (val) => {
  if (_debounceTimer) clearTimeout(_debounceTimer)
  if (!val.trim()) return
  _debounceTimer = setTimeout(() => {
    searchJob(val.trim())
  }, 400)
})

async function searchJob(query: string) {
  if (!query.trim()) {
    Message.warning('请输入岗位名称')
    return
  }
  
  searching.value = true
  try {
    const jobs = await jobApi.search(query, 5)
    if (jobs && jobs.length > 0) {
      const job = jobs[0]
      searchQuery.value = job.title
      await loadGraph(job.title)
      Message.success(`已加载: ${job.title}`)
    } else {
      Message.warning('未找到匹配岗位，尝试直接加载')
      await loadGraph(query)
    }
  } catch (error: any) {
    Message.error(error?.message || '搜索失败')
  } finally {
    searching.value = false
  }
}

onMounted(async () => {
  await loadHotJobs()
  
  if (hotJobs.value.length > 0) {
    const firstJob = hotJobs.value[0].title
    searchQuery.value = firstJob
    await loadGraph(firstJob)
  }
  
  on('click', (params: any) => {
    if (params.data && params.data.id) {
      const job: CareerGraphNode = {
        id: params.data.id,
        title: params.data.name,
      }
      selectJob(job)
    }
  })
})
</script>

<style scoped>
.graph-page {
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
  margin-bottom: 0;
}

.page-header h1 {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.page-header p {
  font-size: 13px;
  color: #888;
  margin: 2px 0 0;
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

.back-btn:hover { background: #f5f5f5; }

.graph-page > .arco-row {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.graph-card {
  height: calc(100vh - 200px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.graph-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f0f7ff;
  border: 1px solid #bae0ff;
  border-radius: 8px;
  padding: 8px 14px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #1677ff;
}

.hint-close {
  margin-left: 12px;
  padding: 2px 10px;
  border: 1px solid #91caff;
  border-radius: 4px;
  background: white;
  color: #1677ff;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.hint-close:hover {
  background: #e6f4ff;
}

.graph-chart {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.info-card {
  margin-top: 16px;
}

.info-card h4 {
  margin-bottom: 8px;
  color: var(--color-text-1);
}

.step-desc {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-3);
}

.transfer-desc {
  font-size: 12px;
  color: var(--color-text-3);
}

.transfer-desc.need-learn {
  color: var(--color-warning);
}

.legend-card {
  margin-top: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin: 8px 0;
}

.legend-color {
  width: 24px;
  height: 4px;
  margin-right: 8px;
  border-radius: 2px;
}

.legend-color.promotion {
  background: #1890ff;
}

.legend-color.transfer {
  background: #52c41a;
}

.legend-color.similar {
  background: #faad14;
}

.hot-jobs-card {
  margin-top: 16px;
}

.hot-job-list {
  display: flex;
  flex-wrap: wrap;
}
</style>
