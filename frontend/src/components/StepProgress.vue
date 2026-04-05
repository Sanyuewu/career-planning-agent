<template>
  <div class="step-progress">
    <div
      v-for="(step, index) in steps"
      :key="step.path"
      class="step-item"
      :class="{
        active: currentStep === index,
        done: currentStep > index,
      }"
    >
      <div class="step-circle" @click="navigateIfDone(index, step.path)">
        <span v-if="currentStep > index" class="step-check">✓</span>
        <span v-else>{{ index + 1 }}</span>
      </div>
      <span class="step-label">{{ step.label }}</span>
      <div v-if="index < steps.length - 1" class="step-connector" :class="{ done: currentStep > index }"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const steps = [
  { label: '上传简历', path: '/upload' },
  { label: '完善画像', path: '/portrait' },
  { label: '岗位匹配', path: '/match' },
  { label: '生成报告', path: '/report' },
]

const currentStep = computed(() => {
  const p = route.path
  if (p.startsWith('/upload')) return 0
  if (p.startsWith('/portrait')) return 1
  if (p.startsWith('/match')) return 2
  if (p.startsWith('/report')) return 3
  return -1
})

function navigateIfDone(index: number, path: string) {
  if (currentStep.value > index) {
    router.push(path)
  }
}
</script>

<style scoped>
.step-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px 32px;
  background: white;
  border-bottom: 1px solid #f0f0f0;
  gap: 0;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.step-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid #d9d9d9;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #999;
  transition: all 0.3s;
  flex-shrink: 0;
}

.step-label {
  font-size: 13px;
  color: #999;
  white-space: nowrap;
  transition: color 0.3s;
}

.step-connector {
  width: 48px;
  height: 2px;
  background: #e8e8e8;
  margin: 0 8px;
  flex-shrink: 0;
  transition: background 0.3s;
}

.step-connector.done {
  background: #667eea;
}

.step-item.active .step-circle {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.step-item.active .step-label {
  color: #667eea;
  font-weight: 600;
}

.step-item.done .step-circle {
  border-color: #667eea;
  background: #667eea;
  color: white;
  cursor: pointer;
}

.step-item.done .step-circle:hover {
  background: #764ba2;
  border-color: #764ba2;
}

.step-item.done .step-label {
  color: #667eea;
}

.step-check {
  font-size: 13px;
}

@media (max-width: 600px) {
  .step-connector {
    width: 24px;
  }
  .step-label {
    display: none;
  }
}
</style>
