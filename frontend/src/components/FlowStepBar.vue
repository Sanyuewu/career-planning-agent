<template>
  <div class="flow-step-bar">
    <div
      v-for="(step, i) in steps"
      :key="step.path"
      class="step-item"
      :class="{
        'step-done': step.done,
        'step-active': step.active,
        'step-pending': !step.done && !step.active,
      }"
      @click="navigate(step)"
    >
      <div class="step-icon">
        <icon-check v-if="step.done" />
        <span v-else>{{ i + 1 }}</span>
      </div>
      <span class="step-label">{{ step.label }}</span>
      <div v-if="i < steps.length - 1" class="step-connector" />
    </div>
  </div>

  <!-- 下一步引导浮层 -->
  <div v-if="nextStep && showGuide" class="next-step-guide">
    <span>下一步：{{ nextStep.label }}</span>
    <a-button size="small" type="primary" @click="navigate(nextStep)">前往</a-button>
    <span class="guide-close" @click="showGuide = false">×</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePortraitStore } from '@/stores/usePortraitStore'
import { useMatchStore } from '@/stores/useMatchStore'

const router = useRouter()
const route = useRoute()
// const userStore = useUserStore()  // 暂时未使用
const portraitStore = usePortraitStore()
const matchStore = useMatchStore()
const showGuide = ref(true)

const FLOW_STEPS = [
  { path: '/upload',  label: '上传简历' },
  { path: '/portrait', label: '学生画像' },
  { path: '/match',   label: '岗位匹配' },
  { path: '/chat',    label: 'AI 对话' },
  { path: '/report',  label: '职业报告' },
]

const steps = computed(() => {
  const currentIdx = FLOW_STEPS.findIndex(s => route.path.startsWith(s.path))
  const hasPortrait = !!portraitStore.portrait?.basicInfo?.name
  const hasMatch = matchStore.results.length > 0

  return FLOW_STEPS.map((s, i) => ({
    ...s,
    active: i === currentIdx,
    done: (() => {
      if (s.path === '/upload') return hasPortrait
      if (s.path === '/portrait') return hasPortrait
      if (s.path === '/match') return hasMatch
      return false
    })(),
  }))
})

const nextStep = computed(() => {
  const currentIdx = FLOW_STEPS.findIndex(s => route.path.startsWith(s.path))
  if (currentIdx < 0 || currentIdx >= FLOW_STEPS.length - 1) return null
  return steps.value[currentIdx + 1]
})

function navigate(step: { path: string }) {
  router.push(step.path)
  showGuide.value = false
}
</script>

<style scoped>
.flow-step-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  background: var(--color-bg-2, #f7f8fa);
  border-bottom: 1px solid var(--color-border, #e5e6eb);
  flex-wrap: wrap;
  gap: 4px;
}

.step-item {
  display: flex;
  align-items: center;
  cursor: pointer;
  position: relative;
  gap: 6px;
  user-select: none;
}

.step-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  background: var(--color-fill-3, #e5e6eb);
  color: var(--color-text-3, #86909c);
  transition: background 0.2s;
}

.step-done .step-icon {
  background: var(--color-success-light-4, #7be188);
  color: #fff;
}
.step-active .step-icon {
  background: rgb(var(--primary-6));
  color: #fff;
}

.step-label {
  font-size: 13px;
  color: var(--color-text-2, #4e5969);
  white-space: nowrap;
}
.step-active .step-label {
  color: rgb(var(--primary-6));
  font-weight: 600;
}
.step-done .step-label {
  color: var(--color-success-6, #00b42a);
}

.step-connector {
  width: 32px;
  height: 2px;
  background: var(--color-border, #e5e6eb);
  margin: 0 4px;
  flex-shrink: 0;
}

.next-step-guide {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: #fff;
  border: 1px solid rgb(var(--primary-6));
  border-radius: 8px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  font-size: 14px;
}
.guide-close {
  cursor: pointer;
  color: var(--color-text-3);
  font-size: 16px;
  line-height: 1;
}

@media (max-width: 768px) {
  .flow-step-bar {
    padding: 8px 8px;
    gap: 2px;
  }
  .step-connector {
    width: 12px;
  }
  .step-label {
    font-size: 11px;
  }
}
</style>
