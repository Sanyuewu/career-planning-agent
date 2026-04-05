<template>
  <div class="market-trend-chart">
    <div class="chart-header">
      <span class="chart-title">📈 市场趋势分析</span>
      <span class="chart-period">近30天</span>
    </div>
    
    <div ref="chartRef" class="chart-container"></div>
    
    <div class="chart-stats" v-if="stats">
      <div class="stat-item">
        <span class="stat-label">平均需求指数</span>
        <span class="stat-value">{{ stats.avgDemand?.toFixed(1) || '-' }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">需求趋势</span>
        <span :class="['stat-value', stats.trendDirection]">
          {{ stats.trendDirection === 'up' ? '↑ 上升' : stats.trendDirection === 'down' ? '↓ 下降' : '→ 平稳' }}
        </span>
      </div>
      <div class="stat-item">
        <span class="stat-label">薪资范围</span>
        <span class="stat-value salary">
          {{ stats.minSalary?.toFixed(0) || '-' }}k - {{ stats.maxSalary?.toFixed(0) || '-' }}k
        </span>
      </div>
    </div>
    
    <div class="chart-legend">
      <div class="legend-item">
        <span class="legend-color demand"></span>
        <span>需求指数</span>
      </div>
      <div class="legend-item">
        <span class="legend-color salary"></span>
        <span>平均薪资(K)</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

interface TrendPoint {
  date: string
  demand_index?: number
  jd_count?: number
  avg_salary?: number
}

interface Stats {
  avgDemand?: number
  trendDirection?: 'up' | 'down' | 'stable'
  minSalary?: number
  maxSalary?: number
}

interface Props {
  jobName: string
  trendData: TrendPoint[]
}

const props = defineProps<Props>()

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const stats = ref<Stats>({})

function processTrendData(data: TrendPoint[]) {
  if (!data || data.length === 0) return { dates: [], demands: [], salaries: [] }
  
  const dates = data.map(d => d.date)
  const demands = data.map(d => d.demand_index || 0)
  const salaries = data.map(d => d.avg_salary || 0)
  
  const validDemands = demands.filter(d => d > 0)
  const validSalaries = salaries.filter(s => s > 0)
  
  if (validDemands.length >= 2) {
    const firstHalf = validDemands.slice(0, Math.floor(validDemands.length / 2))
    const secondHalf = validDemands.slice(Math.floor(validDemands.length / 2))
    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length
    
    stats.value.avgDemand = validDemands.reduce((a, b) => a + b, 0) / validDemands.length
    stats.value.trendDirection = secondAvg > firstAvg * 1.1 ? 'up' : secondAvg < firstAvg * 0.9 ? 'down' : 'stable'
  }
  
  if (validSalaries.length > 0) {
    stats.value.minSalary = Math.min(...validSalaries)
    stats.value.maxSalary = Math.max(...validSalaries)
  }
  
  return { dates, demands, salaries }
}

function renderChart() {
  if (!chartRef.value || !props.trendData?.length) return
  
  if (!chart) {
    chart = echarts.init(chartRef.value)
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartRef.value)
  }
  
  const { dates, demands, salaries } = processTrendData(props.trendData)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#333', fontSize: 12 },
      formatter: (params: any) => {
        let html = `<div style="font-weight:600;margin-bottom:8px">${params[0].axisValue}</div>`
        params.forEach((item: any) => {
          const value = item.seriesName === '平均薪资' 
            ? `${item.value?.toFixed(1) || '-'}K` 
            : item.value?.toFixed(1) || '-'
          html += `<div style="display:flex;justify-content:space-between;gap:20px;">
            <span>${item.marker} ${item.seriesName}</span>
            <span style="font-weight:600">${value}</span>
          </div>`
        })
        return html
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
      data: dates,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { 
        color: '#999', 
        fontSize: 10,
        interval: Math.floor(dates.length / 6),
        rotate: 30
      },
      axisTick: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        name: '需求指数',
        nameTextStyle: { color: '#999', fontSize: 10 },
        axisLine: { show: false },
        axisLabel: { color: '#999', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      {
        type: 'value',
        name: '薪资(K)',
        nameTextStyle: { color: '#999', fontSize: 10 },
        axisLine: { show: false },
        axisLabel: { color: '#999', fontSize: 10, formatter: '{value}K' },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '需求指数',
        type: 'line',
        data: demands,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#667eea', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
            { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
          ])
        },
        itemStyle: { color: '#667eea' }
      },
      {
        name: '平均薪资',
        type: 'line',
        yAxisIndex: 1,
        data: salaries,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#52c41a', width: 2, type: 'dashed' },
        itemStyle: { color: '#52c41a' }
      }
    ]
  }
  
  chart.setOption(option, true)
}

watch(() => props.trendData, () => {
  renderChart()
}, { deep: true })

onMounted(() => {
  renderChart()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<style scoped>
.market-trend-chart {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.chart-period {
  font-size: 12px;
  color: #999;
  background: white;
  padding: 2px 8px;
  border-radius: 10px;
}

.chart-container {
  width: 100%;
  height: 200px;
}

.chart-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e8e8e8;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.stat-value.up {
  color: #52c41a;
}

.stat-value.down {
  color: #f5222d;
}

.stat-value.stable {
  color: #faad14;
}

.stat-value.salary {
  color: #667eea;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
}

.legend-color {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.legend-color.demand {
  background: #667eea;
}

.legend-color.salary {
  background: #52c41a;
}
</style>
