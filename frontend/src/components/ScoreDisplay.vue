<template>
  <span :class="['score-display', size, scoreClass]">
    <span class="score-value">{{ displayValue }}</span>
    <span class="score-unit" v-if="showUnit">{{ unit }}</span>
    <span class="score-label" v-if="label">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  score: number
  maxScore?: number
  showUnit?: boolean
  unit?: string
  label?: string
  size?: 'small' | 'medium' | 'large'
  decimals?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxScore: 100,
  showUnit: false,
  unit: '分',
  size: 'medium',
  decimals: 0
})

const displayValue = computed(() => {
  if (props.decimals > 0) {
    return props.score.toFixed(props.decimals)
  }
  return Math.round(props.score)
})

const scoreClass = computed(() => {
  const percentage = (props.score / props.maxScore) * 100
  if (percentage >= 80) return 'excellent'
  if (percentage >= 60) return 'good'
  if (percentage >= 40) return 'average'
  return 'poor'
})
</script>

<style scoped>
.score-display {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-weight: 600;
}

.score-display.small {
  font-size: 14px;
}

.score-display.medium {
  font-size: 18px;
}

.score-display.large {
  font-size: 24px;
}

.score-value {
  font-weight: 700;
}

.score-unit {
  font-size: 0.7em;
  font-weight: 500;
  opacity: 0.8;
}

.score-label {
  font-size: 0.6em;
  font-weight: 400;
  opacity: 0.6;
  margin-left: 4px;
}

.score-display.excellent .score-value {
  color: #52c41a;
}

.score-display.good .score-value {
  color: #1890ff;
}

.score-display.average .score-value {
  color: #faad14;
}

.score-display.poor .score-value {
  color: #f5222d;
}

.score-display.excellent .score-unit {
  color: #52c41a;
}

.score-display.good .score-unit {
  color: #1890ff;
}

.score-display.average .score-unit {
  color: #faad14;
}

.score-display.poor .score-unit {
  color: #f5222d;
}
</style>
