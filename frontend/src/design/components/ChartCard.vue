<template>
  <div ref="el" class="chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = withDefaults(defineProps<{ option: EChartsOption | null; height?: number }>(), { height: 280 })
const el = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  if (props.option) chart.setOption(props.option, true)
}
function resize() { chart?.resize() }

onMounted(() => { render(); window.addEventListener('resize', resize) })
onUnmounted(() => { window.removeEventListener('resize', resize); chart?.dispose(); chart = null })
watch(() => props.option, () => nextTick(render), { deep: true })
</script>

<style scoped>
.chart { width: 100%; }
</style>
