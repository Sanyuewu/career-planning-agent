<template>
  <div class="competitiveness-gauge">
    <div class="gauge-header">
      <h4>{{ title }}</h4>
      <div class="header-right">
        <span class="level-badge" :class="levelClass">{{ levelLabel }}</span>
        <button class="info-btn" @click="showLevelInfo = true">
          <span>?</span>
        </button>
      </div>
    </div>
    
    <div ref="chartRef" class="gauge-container"></div>
    
    <div class="gauge-details">
      <div class="detail-row">
        <span class="detail-label">竞争力得分</span>
        <span class="detail-value">{{ Math.round(animatedScore) }}分</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">超越用户</span>
        <span class="detail-value highlight">{{ beatPercent }}%</span>
      </div>
      <div class="detail-row" v-if="peerComparison">
        <span class="detail-label">同专业排名</span>
        <span class="detail-value highlight">前{{ 100 - peerComparison.same_major.percentile }}%</span>
      </div>
    </div>

    <div class="trend-section" v-if="history.length > 1">
      <div class="trend-header">
        <h5>竞争力趋势</h5>
        <span class="trend-badge" :class="trendDirection">
          {{ trendDirection === 'up' ? '↑ 上升' : trendDirection === 'down' ? '↓ 下降' : '→ 稳定' }}
        </span>
      </div>
      <div ref="trendChartRef" class="trend-chart"></div>
    </div>

    <div class="dimension-scores" v-if="dimensions.length > 0">
      <div class="dimension-item" v-for="dim in dimensions" :key="dim.name">
        <div class="dim-header">
          <span class="dim-name">{{ dim.name }}</span>
          <span class="dim-score">{{ Math.round(dim.score) }}</span>
        </div>
        <div class="dim-bar">
          <div 
            class="dim-fill" 
            :style="{ width: dim.score + '%' }"
            :class="getDimClass(dim.score)"
          ></div>
        </div>
      </div>
    </div>

    <div class="suggestions" v-if="suggestions.length > 0">
      <h5>提升建议</h5>
      <ul>
        <li v-for="(suggestion, idx) in suggestions.slice(0, 3)" :key="idx">
          {{ suggestion }}
        </li>
      </ul>
    </div>

    <a-modal v-model:visible="showLevelInfo" :footer="false" title="竞争力等级说明" width="400px">
      <div class="level-info-content">
        <div class="level-item" v-for="info in levelInfoList" :key="info.level">
          <span class="level-badge" :class="info.class">{{ info.level }}</span>
          <span class="level-range">{{ info.range }}</span>
          <span class="level-desc">{{ info.desc }}</span>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import type { CompetitivenessHistoryItem, PeerComparisonData } from '../api/stats'

interface DimensionScore {
  name: string
  score: number
}

const props = withDefaults(defineProps<{
  title?: string
  score: number
  level?: string
  dimensions?: DimensionScore[]
  suggestions?: string[]
  history?: CompetitivenessHistoryItem[]
  peerComparison?: PeerComparisonData | null
}>(), {
  title: '竞争力评估',
  score: 0,
  level: '',
  dimensions: () => [],
  suggestions: () => [],
  history: () => [],
  peerComparison: null
})

const chartRef = ref<HTMLElement | null>(null)
const trendChartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let trendChartInstance: echarts.ECharts | null = null
const showLevelInfo = ref(false)
const animatedScore = ref(0)

const levelClass = computed(() => {
  if (props.score >= 80) return 'excellent'
  if (props.score >= 60) return 'good'
  if (props.score >= 40) return 'average'
  return 'weak'
})

const levelLabel = computed(() => {
  if (props.level) return props.level
  if (props.score >= 80) return '优秀'
  if (props.score >= 60) return '良好'
  if (props.score >= 40) return '一般'
  return '待提升'
})

const beatPercent = computed(() => {
  if (props.peerComparison) {
    return props.peerComparison.same_major.percentile
  }
  return Math.min(99, Math.round(props.score * 0.8 + 10))
})

const trendDirection = computed(() => {
  if (props.history.length < 2) return 'stable'
  const recent = props.history.slice(-2)
  const diff = recent[1].score - recent[0].score
  if (diff > 3) return 'up'
  if (diff < -3) return 'down'
  return 'stable'
})

const levelInfoList = [
  { level: '优秀', class: 'excellent', range: '80-100分', desc: '综合能力强，竞争力领先' },
  { level: '良好', class: 'good', range: '60-79分', desc: '基础扎实，有提升空间' },
  { level: '一般', class: 'average', range: '40-59分', desc: '需要加强核心能力' },
  { level: '待提升', class: 'weak', range: '0-39分', desc: '建议全面提升各项能力' },
]

function getDimClass(score: number): string {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'average'
  return 'weak'
}

function animateScore(target: number) {
  const duration = 1000
  const start = animatedScore.value
  const startTime = performance.now()
  
  function animate(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeProgress = 1 - Math.pow(1 - progress, 3)
    animatedScore.value = start + (target - start) * easeProgress
    
    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }
  
  requestAnimationFrame(animate)
}

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  
  window.addEventListener('resize', handleResize)
}

function initTrendChart() {
  if (!trendChartRef.value || props.history.length < 2) return
  
  trendChartInstance = echarts.init(trendChartRef.value)
  updateTrendChart()
}

function handleResize() {
  chartInstance?.resize()
  trendChartInstance?.resize()
}

function updateChart() {
  if (!chartInstance) return
  
  const option: EChartsOption = {
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        splitNumber: 10,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#ff4d4f' },
              { offset: 0.5, color: '#faad14' },
              { offset: 1, color: '#52c41a' }
            ]
          }
        },
        progress: {
          show: true,
          width: 20,
          roundCap: true
        },
        pointer: {
          show: false
        },
        axisLine: {
          lineStyle: {
            width: 20,
            color: [[1, '#f0f0f0']]
          },
          roundCap: true
        },
        axisTick: {
          show: false
        },
        splitLine: {
          show: false
        },
        axisLabel: {
          show: false
        },
        title: {
          show: false
        },
        detail: {
          valueAnimation: true,
          fontSize: 36,
          fontWeight: 700,
          color: '#1a1a2e',
          offsetCenter: [0, '10%'],
          formatter: () => {
            return Math.round(animatedScore.value).toString()
          }
        },
        data: [
          {
            value: props.score
          }
        ]
      }
    ]
  }
  
  chartInstance.setOption(option)
}

function updateTrendChart() {
  if (!trendChartInstance || props.history.length < 2) return
  
  const dates = props.history.map(h => h.date.slice(5))
  const scores = props.history.map(h => h.score)
  
  const option: EChartsOption = {
    grid: {
      left: 30,
      right: 10,
      top: 10,
      bottom: 20
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: '#999' }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { fontSize: 10, color: '#999' }
    },
    series: [{
      type: 'line',
      data: scores,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#667eea', width: 2 },
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
      itemStyle: { color: '#667eea' }
    }]
  }
  
  trendChartInstance.setOption(option)
}

watch(() => props.score, (newScore) => {
  animateScore(newScore)
  updateChart()
})

watch(() => props.history, async () => {
  await nextTick()
  if (!trendChartInstance) {
    initTrendChart()
  } else {
    updateTrendChart()
  }
}, { deep: true })

onMounted(() => {
  initChart()
  animateScore(props.score)
  if (props.history.length > 1) {
    nextTick(() => initTrendChart())
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  trendChartInstance?.dispose()
})
</script>

<style scoped>
.competitiveness-gauge {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.gauge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.gauge-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-btn {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid #ddd;
  background: #f5f5f5;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.info-btn:hover {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

.level-badge {
  padding: 4px 14px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.level-badge.excellent {
  background: #f6ffed;
  color: #52c41a;
}

.level-badge.good {
  background: #e6f7ff;
  color: #1890ff;
}

.level-badge.average {
  background: #fff7e6;
  color: #fa8c16;
}

.level-badge.weak {
  background: #fff1f0;
  color: #f5222d;
}

.gauge-container {
  width: 100%;
  height: 180px;
}

.gauge-details {
  display: flex;
  justify-content: space-around;
  margin-top: 8px;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: #999;
}

.detail-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}

.detail-value.highlight {
  color: #667eea;
}

.trend-section {
  margin-top: 16px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.trend-header h5 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.trend-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.trend-badge.up {
  background: #f6ffed;
  color: #52c41a;
}

.trend-badge.down {
  background: #fff1f0;
  color: #f5222d;
}

.trend-badge.stable {
  background: #f0f0f0;
  color: #666;
}

.trend-chart {
  width: 100%;
  height: 80px;
}

.dimension-scores {
  margin-top: 16px;
}

.dimension-item {
  margin-bottom: 12px;
}

.dimension-item:last-child {
  margin-bottom: 0;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.dim-name {
  font-size: 13px;
  color: #333;
}

.dim-score {
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
}

.dim-bar {
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.dim-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.dim-fill.excellent {
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
}

.dim-fill.good {
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
}

.dim-fill.average {
  background: linear-gradient(90deg, #faad14 0%, #ffc53d 100%);
}

.dim-fill.weak {
  background: linear-gradient(90deg, #ff4d4f 0%, #ff7875 100%);
}

.suggestions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.suggestions h5 {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 10px;
}

.suggestions ul {
  margin: 0;
  padding-left: 18px;
}

.suggestions li {
  font-size: 13px;
  color: #666;
  line-height: 1.8;
}

.level-info-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.level-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.level-item:last-child {
  border-bottom: none;
}

.level-range {
  font-size: 13px;
  color: #666;
  min-width: 70px;
}

.level-desc {
  font-size: 13px;
  color: #333;
}

@media (max-width: 768px) {
  .gauge-container {
    height: 150px;
  }
  
  .gauge-details {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
