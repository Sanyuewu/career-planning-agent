<template>
  <div class="stepper">
    <div v-for="(s, i) in steps" :key="s.key" class="step"
         :class="{ done: s.done, active: s.active, clickable: !!s.to }"
         @click="s.to && router.push(s.to)">
      <div class="dot">
        <span v-if="s.done">✓</span><span v-else>{{ i + 1 }}</span>
      </div>
      <div class="lbl">{{ s.label }}</div>
      <div v-if="i < steps.length - 1" class="line" :class="{ filled: s.done }"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
export interface JourneyStep { key: string; label: string; done: boolean; active?: boolean; to?: string }
defineProps<{ steps: JourneyStep[] }>()
const router = useRouter()
</script>

<style scoped>
.stepper { display: flex; align-items: flex-start; }
.step { position: relative; flex: 1; display: flex; flex-direction: column; align-items: center; }
.step.clickable { cursor: pointer; }
.step.clickable:hover .dot { border-color: var(--c-primary); }
.step.clickable:hover .lbl { color: var(--c-primary); }
.dot {
  width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: var(--fz-2); font-weight: 800; background: var(--c-surface);
  border: 2px solid var(--c-border-2); color: var(--c-text-3); z-index: 1; transition: all .2s;
}
.step.done .dot { background: var(--c-growth); border-color: var(--c-growth); color: #fff; }
.step.active .dot { border-color: var(--c-primary); color: var(--c-primary); box-shadow: 0 0 0 4px var(--c-primary-weak); }
.lbl { font-size: var(--fz-2); color: var(--c-text-2); margin-top: 6px; }
.step.active .lbl { color: var(--c-primary); font-weight: 700; }
.step.done .lbl { color: var(--c-text); }
.line { position: absolute; top: 14px; left: 50%; width: 100%; height: 2px; background: var(--c-border-2); z-index: 0; }
.line.filled { background: var(--c-growth); }
</style>
