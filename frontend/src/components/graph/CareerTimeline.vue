<template>
  <div class="career-timeline">
    <div class="timeline-header">
      <h4>薪资成长曲线</h4>
      <div class="view-toggle">
        <button 
          :class="['toggle-btn', { active: viewMode === 'chart' }]" 
          @click="viewMode = 'chart'"
        >图表</button>
        <button 
          :class="['toggle-btn', { active: viewMode === 'timeline' }]" 
          @click="viewMode = 'timeline'"
        >时间轴</button>
      </div>
    </div>
    
    <div v-if="loading" class="timeline-loading">
      <a-spin />
      <span>加载中...</span>
    </div>
    
    <template v-else-if="promotionPath.length > 0">
      <div v-show="viewMode === 'chart'" ref="chartRef" class="timeline-chart"></div>
      
      <div v-show="viewMode === 'timeline'" class="timeline-list">
        <div 
          v-for="(step, index) in promotionPath" 
          :key="index"
          class="timeline-item"
          :class="{ 'is-current': index === 0 }"
        >
          <div class="timeline-dot">
            <span v-if="index === 0" class="current-badge">当前</span>
            <span v-else class="step-num">{{ index }}</span>
          </div>
          <div class="timeline-content">
            <div class="step-header">
              <span class="step-title">{{ step.title }}</span>
              <span class="step-years" v-if="step.years">{{ step.years }}</span>
            </div>
            <div class="step-salary" v-if="step.salary">
              <span class="salary-label">薪资范围</span>
              <span class="salary-value">{{ step.salary }}</span>
            </div>
            <div class="step-desc" v-if="step.description">{{ step.description }}</div>
            <div class="step-skills" v-if="step.skills && step.skills.length">
              <span class="skill-tag" v-for="skill in step.skills.slice(0, 4)" :key="skill">
                {{ skill }}
              </span>
            </div>
          </div>
          <div class="timeline-arrow" v-if="index < promotionPath.length - 1">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path fill="currentColor" d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
            </svg>
          </div>
        </div>
      </div>
    </template>
    
    <a-empty v-else description="暂无晋升路径数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { jobApi } from '../../api/job'

interface Props {
  jobName: string
}

const props = defineProps<Props>()

const chartRef = ref<HTMLElement | null>(null)
const loading = ref(false)
const viewMode = ref<'chart' | 'timeline'>('chart')
const promotionPath = ref<any[]>([])
let chartInstance: echarts.ECharts | null = null

const chartData = computed(() => {
  if (promotionPath.value.length === 0) return null
  
  const years = ['入职']
  let accYears = 0
  for (let i = 1; i < promotionPath.value.length; i++) {
    const step = promotionPath.value[i]
    const y = parseInt(step.years?.match(/\d+/)?.[0] || '2')
    accYears += y
    years.push(`+${accYears}年`)
  }
  
  const salaries = promotionPath.value.map(step => {
    const salary = step.salary || ''
    const match = salary.match(/(\d+)-(\d+)/)
    if (match) {
      return (parseInt(match[1]) + parseInt(match[2])) / 2
    }
    const singleMatch = salary.match(/(\d+)/)
    return singleMatch ? parseInt(singleMatch[1]) : 15
  })
  
  return { years, salaries }
})

function renderChart() {
  if (!chartRef.value || !chartData.value) return
  
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  
  const { years, salaries } = chartData.value
  
  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const idx = params[0].dataIndex
        const step = promotionPath.value[idx]
        return `
          <div style="font-weight:600;margin-bottom:4px">${step.title}</div>
          <div>薪资：${step.salary || '面议'}</div>
          <div>年限：${step.years || '-'}</div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#e5e5e5' } },
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '薪资(k/月)',
      nameTextStyle: { color: '#999', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#666', fontSize: 11 }
    },
    series: [{
      type: 'line',
      data: salaries,
      smooth: true,
      symbol: 'circle',
      symbolSize: 10,
      lineStyle: {
        color: '#667eea',
        width: 3
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(102,126,234,0.3)' },
            { offset: 1, color: 'rgba(102,126,234,0.05)' }
          ]
        }
      },
      itemStyle: {
        color: '#667eea',
        borderColor: '#fff',
        borderWidth: 2
      },
      emphasis: {
        itemStyle: {
          color: '#764ba2',
          borderColor: '#fff',
          borderWidth: 3,
          shadowBlur: 10,
          shadowColor: 'rgba(102,126,234,0.5)'
        }
      },
      markPoint: {
        data: [
          { type: 'max', name: '最高', itemStyle: { color: '#52c41a' } },
          { type: 'min', name: '起点', itemStyle: { color: '#fa8c16' } }
        ],
        symbol: 'pin',
        symbolSize: 40,
        label: { color: '#fff', fontSize: 10 }
      }
    }]
  }, true)
}

async function loadPathData() {
  if (!props.jobName) return
  
  loading.value = true
  try {
    const data = await jobApi.getCareerGraph(props.jobName)
    
    if (data.promotion_paths && data.promotion_paths.length > 0) {
      const mainPath = data.promotion_paths[0]
      promotionPath.value = (mainPath.nodes || []).map((n: { title?: string; name?: string; salary?: string; skills?: string[]; overview?: string }, idx: number) => {
        const trans = (mainPath.transitions && mainPath.transitions[idx]) || {}
        return {
          title: n?.title || n?.name || '',
          years: (trans as { years?: string }).years || '',
          salary: n?.salary || '',
          description: (trans as { description?: string }).description || n?.overview || '',
          skills: n?.skills || []
        }
      }).filter((s: { title: string }) => s.title)
    } else {
      const nodes = data.nodes || []
      const edges = data.edges || []
      
      const jobNodes = nodes.filter((n: { id?: string; node_type?: string }) => n.id?.startsWith('job_') || n.node_type === 'Job')
      const promoteEdges = edges.filter((e: { type?: string }) => e.type === 'PROMOTES_TO')
      
      if (jobNodes.length > 0) {
        promotionPath.value = jobNodes.slice(0, 5).map((n: { id?: string; title?: string; name?: string; salary?: string; attrs?: { salary?: string; skills?: string[] }; skills?: string[] }) => {
          const edge = promoteEdges.find((e: { from?: string; to?: string }) => e.from === n.id || e.to === n.id) || {}
          return {
            title: n.title || n.name || '',
            years: (edge as { label?: string }).label || '',
            salary: n.salary || n.attrs?.salary || '',
            description: (edge as { description?: string }).description || '',
            skills: n.skills || n.attrs?.skills || []
          }
        })
      }
    }
    
    if (viewMode.value === 'chart') {
      setTimeout(renderChart, 100)
    }
  } catch (err) {
    console.error('加载晋升路径失败:', err)
  } finally {
    loading.value = false
  }
}

watch(() => props.jobName, loadPathData, { immediate: true })

watch(viewMode, (mode) => {
  if (mode === 'chart') {
    setTimeout(renderChart, 50)
  }
})

onMounted(() => {
  window.addEventListener('resize', () => chartInstance?.resize())
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', () => chartInstance?.resize())
})
</script>

<style scoped>
.career-timeline {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.timeline-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.view-toggle {
  display: flex;
  gap: 4px;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 2px;
}

.toggle-btn {
  padding: 4px 12px;
  border: none;
  background: transparent;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: #667eea;
  color: #fff;
}

.toggle-btn:hover:not(.active) {
  background: #e8e8e8;
}

.timeline-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
  color: #999;
}

.timeline-chart {
  width: 100%;
  height: 280px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  position: relative;
  padding-bottom: 20px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-item.is-current .timeline-dot {
  background: linear-gradient(135deg, #667eea, #764ba2);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.timeline-item.is-current .timeline-content {
  background: linear-gradient(135deg, rgba(102,126,234,0.08), rgba(118,75,162,0.08));
  border-color: #667eea;
}

.timeline-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.current-badge {
  font-size: 10px;
  color: #fff;
  font-weight: 600;
}

.step-num {
  font-size: 14px;
  font-weight: 600;
  color: #666;
}

.timeline-content {
  flex: 1;
  background: #fafafa;
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 12px 14px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}

.step-years {
  font-size: 12px;
  color: #667eea;
  background: rgba(102,126,234,0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.step-salary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.salary-label {
  font-size: 11px;
  color: #999;
}

.salary-value {
  font-size: 13px;
  font-weight: 600;
  color: #52c41a;
}

.step-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 8px;
}

.step-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.skill-tag {
  font-size: 11px;
  color: #667eea;
  background: rgba(102,126,234,0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

.timeline-arrow {
  position: absolute;
  left: 18px;
  bottom: -4px;
  color: #ddd;
  z-index: 0;
}
</style>
