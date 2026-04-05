import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'

export function useECharts(containerRef: { value: HTMLElement | null }) {
  const chart = ref<ECharts | null>(null)
  const loading = ref(false)
  
  function initChart() {
    if (!containerRef.value) return
    
    if (chart.value) {
      chart.value.dispose()
    }
    
    chart.value = echarts.init(containerRef.value)
    
    const resizeObserver = new ResizeObserver(() => {
      chart.value?.resize()
    })
    
    resizeObserver.observe(containerRef.value)
    
    return () => {
      resizeObserver.disconnect()
    }
  }
  
  function setOption(option: EChartsOption, notMerge: boolean = false) {
    if (!chart.value) {
      initChart()
    }
    chart.value?.setOption(option, notMerge)
  }
  
  function showLoading() {
    loading.value = true
    chart.value?.showLoading()
  }
  
  function hideLoading() {
    loading.value = false
    chart.value?.hideLoading()
  }
  
  function resize() {
    chart.value?.resize()
  }
  
  function dispose() {
    chart.value?.dispose()
    chart.value = null
  }
  
  function on(event: string, handler: (...args: any[]) => void) {
    chart.value?.on(event, handler)
  }
  
  function off(event: string, handler?: (...args: any[]) => void) {
    chart.value?.off(event, handler)
  }
  
  onMounted(() => {
    initChart()
    window.addEventListener('resize', resize)
  })
  
  onUnmounted(() => {
    window.removeEventListener('resize', resize)
    dispose()
  })
  
  return {
    chart,
    loading,
    initChart,
    setOption,
    showLoading,
    hideLoading,
    resize,
    dispose,
    on,
    off,
  }
}

export function createRadarChartOption(
  dimensions: { name: string; max: number }[],
  values: number[],
  title: string = ''
): EChartsOption {
  return {
    title: {
      text: title,
      left: 'center',
    },
    tooltip: {
      trigger: 'item',
    },
    radar: {
      indicator: dimensions,
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#666',
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: '匹配度',
            areaStyle: {
              color: 'rgba(24, 144, 255, 0.3)',
            },
            lineStyle: {
              color: '#1890ff',
            },
            itemStyle: {
              color: '#1890ff',
            },
          },
        ],
      },
    ],
  }
}

export function createForceGraphOption(
  nodes: { id: string; name: string; category?: number }[],
  edges: { source: string; target: string; value?: number; lineStyle?: any; label?: any }[],
  categories?: { name: string }[],
  layoutConfig: any = {}
): EChartsOption {
  return {
    tooltip: {},
    legend: {
      data: categories?.map(c => c.name) || [],
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        ...layoutConfig,
        data: nodes.map(n => ({
          name: n.name,
          id: n.id,
          category: n.category,
        })),
        links: edges.map(e => ({
          source: e.source,
          target: e.target,
          value: e.value,
          lineStyle: e.lineStyle,
          label: e.label,
        })),
        categories,
        roam: true,
        label: {
          show: true,
          position: 'right',
        },
        force: {
          repulsion: 100,
          edgeLength: 50,
          ...layoutConfig.force,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 3,
          },
        },
      },
    ],
  }
}
