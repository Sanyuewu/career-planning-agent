<template>
  <div :class="['progress-bar-wrapper', size]">
    <div class="progress-info" v-if="showLabel || showPercent">
      <span class="progress-label" v-if="showLabel">{{ label }}</span>
      <span class="progress-percent">{{ displayPercent }}%</span>
    </div>
    
    <div class="progress-track">
      <div 
        class="progress-fill"
        :style="fillStyle"
        :class="statusClass"
      >
        <div class="progress-shine" v-if="animated"></div>
      </div>
    </div>
    
    <div class="progress-steps" v-if="steps.length > 0">
      <div 
        v-for="(step, index) in steps" 
        :key="index"
        :class="['progress-step', { 
          active: currentStep >= index,
          completed: currentStep > index 
        }]"
      >
        <span class="step-dot">{{ currentStep > index ? '✓' : index + 1 }}</span>
        <span class="step-label">{{ step }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  percent: number
  label?: string
  size?: 'small' | 'medium' | 'large'
  status?: 'normal' | 'success' | 'warning' | 'error' | 'active'
  showLabel?: boolean
  showPercent?: boolean
  animated?: boolean
  steps?: string[]
  currentStep?: number
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  status: 'normal',
  showLabel: false,
  showPercent: true,
  animated: false,
  steps: () => [],
  currentStep: 0
})

const displayPercent = computed(() => {
  return Math.min(100, Math.max(0, Math.round(props.percent)))
})

const statusClass = computed(() => {
  if (props.status !== 'normal') return props.status
  if (displayPercent.value >= 100) return 'success'
  if (displayPercent.value >= 70) return 'active'
  if (displayPercent.value >= 30) return 'warning'
  return 'error'
})

const fillStyle = computed(() => {
  if (props.color) {
    return {
      width: `${displayPercent.value}%`,
      background: props.color
    }
  }
  return { width: `${displayPercent.value}%` }
})
</script>

<style scoped>
.progress-bar-wrapper {
  width: 100%;
}

.progress-bar-wrapper.small {
  --track-height: 6px;
  --font-size: 12px;
}

.progress-bar-wrapper.medium {
  --track-height: 10px;
  --font-size: 14px;
}

.progress-bar-wrapper.large {
  --track-height: 16px;
  --font-size: 16px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: var(--font-size);
}

.progress-label {
  color: #666;
  font-weight: 500;
}

.progress-percent {
  color: #333;
  font-weight: 600;
}

.progress-track {
  width: 100%;
  height: var(--track-height);
  background: #f0f0f0;
  border-radius: calc(var(--track-height) / 2);
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  border-radius: calc(var(--track-height) / 2);
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
}

.progress-fill.normal {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.progress-fill.active {
  background: linear-gradient(90deg, #faad14 0%, #fa8c16 100%);
}

.progress-fill.success {
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
}

.progress-fill.warning {
  background: linear-gradient(90deg, #faad14 0%, #ffc53d 100%);
}

.progress-fill.error {
  background: linear-gradient(90deg, #f5222d 0%, #ff4d4f 100%);
}

.progress-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.3) 50%,
    transparent 100%
  );
  animation: shine 2s infinite;
}

@keyframes shine {
  0% { left: -100%; }
  100% { left: 100%; }
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #999;
  transition: all 0.3s;
}

.progress-step.active .step-dot {
  background: #667eea;
  color: white;
}

.progress-step.completed .step-dot {
  background: #52c41a;
  color: white;
}

.step-label {
  font-size: 12px;
  color: #999;
  text-align: center;
}

.progress-step.active .step-label {
  color: #667eea;
  font-weight: 500;
}

.progress-step.completed .step-label {
  color: #52c41a;
}
</style>
