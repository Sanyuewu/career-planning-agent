<template>
  <div class="skill-radar-chart">
    <div class="chart-header">
      <h4>{{ title }}</h4>
      <div class="legend" v-if="showLegend">
        <span class="legend-item">
          <span class="legend-dot current"></span>
          <span>当前水平</span>
        </span>
        <span class="legend-item" v-if="compareData">
          <span class="legend-dot target"></span>
          <span>目标要求</span>
        </span>
      </div>
    </div>
    <div ref="chartRef" class="chart-container"></div>
    <div class="skill-summary" v-if="skills.length > 0">
      <div class="summary-item" v-for="skill in topSkills" :key="skill.name">
        <span class="skill-name">{{ skill.name }}</span>
        <div class="skill-bar">
          <div 
            class="skill-fill" 
            :style="{ width: skill.value + '%' }"
            :class="getSkillClass(skill.value)"
          ></div>
        </div>
        <span class="skill-value">{{ skill.value }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

interface SkillData {
  name: string
  value: number
  maxValue?: number
}

const props = withDefaults(defineProps<{
  title?: string
  skills: SkillData[]
  compareData?: SkillData[]
  showLegend?: boolean
  showSummary?: boolean
  maxSkillValue?: number
}>(), {
  title: '技能雷达图',
  showLegend: true,
  showSummary: true,
  maxSkillValue: 100
})

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const topSkills = computed(() => {
  return [...props.skills]
    .sort((a, b) => b.value - a.value)
    .slice(0, 5)
})

function getSkillClass(value: number): string {
  if (value >= 80) return 'excellent'
  if (value >= 60) return 'good'
  if (value >= 40) return 'average'
  return 'weak'
}

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  chartInstance?.resize()
}

function updateChart() {
  if (!chartInstance) return
  
  const indicators = props.skills.map(skill => ({
    name: skill.name,
    max: skill.maxValue || props.maxSkillValue
  }))
  
  const radarData: Array<{
    value: number[]
    name: string
    symbol: string
    symbolSize: number
    lineStyle: { color: string; width: number; type?: 'solid' | 'dashed' | 'dotted' }
    areaStyle: { color: string }
    itemStyle: { color: string }
  }> = [
    {
      value: props.skills.map(s => s.value),
      name: '当前水平',
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        color: '#667eea',
        width: 2
      },
      areaStyle: {
        color: 'rgba(102, 126, 234, 0.3)'
      },
      itemStyle: {
        color: '#667eea'
      }
    }
  ]
  
  if (props.compareData && props.compareData.length > 0) {
    radarData.push({
      value: props.compareData.map(s => s.value),
      name: '目标要求',
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        color: '#52c41a',
        width: 2,
        type: 'dashed'
      },
      areaStyle: {
        color: 'rgba(82, 196, 26, 0.2)'
      },
      itemStyle: {
        color: '#52c41a'
      }
    })
  }
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data
        let html = `<div style="font-weight: 600; margin-bottom: 8px;">${data.name}</div>`
        data.value.forEach((val: number, idx: number) => {
          html += `<div style="display: flex; justify-content: space-between; gap: 20px;">
            <span>${indicators[idx].name}:</span>
            <span style="font-weight: 600;">${val}%</span>
          </div>`
        })
        return html
      }
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#666',
        fontSize: 12,
        fontWeight: 500
      },
      splitLine: {
        lineStyle: {
          color: '#e5e5e5'
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['#fff', '#fafafa']
        }
      },
      axisLine: {
        lineStyle: {
          color: '#e5e5e5'
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: radarData
      }
    ]
  }
  
  chartInstance.setOption(option)
}

watch(() => [props.skills, props.compareData], () => {
  updateChart()
}, { deep: true })

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.skill-radar-chart {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.current {
  background: #667eea;
}

.legend-dot.target {
  background: #52c41a;
}

.chart-container {
  width: 100%;
  height: 280px;
}

.skill-summary {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.summary-item:last-child {
  margin-bottom: 0;
}

.skill-name {
  min-width: 80px;
  font-size: 13px;
  color: #333;
}

.skill-bar {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.skill-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.skill-fill.excellent {
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
}

.skill-fill.good {
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
}

.skill-fill.average {
  background: linear-gradient(90deg, #faad14 0%, #ffc53d 100%);
}

.skill-fill.weak {
  background: linear-gradient(90deg, #ff4d4f 0%, #ff7875 100%);
}

.skill-value {
  min-width: 40px;
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  text-align: right;
}

@media (max-width: 768px) {
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .chart-container {
    height: 240px;
  }
  
  .skill-name {
    min-width: 60px;
    font-size: 12px;
  }
}
</style>
