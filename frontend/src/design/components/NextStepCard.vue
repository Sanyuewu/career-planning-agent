<template>
  <div class="next" @click="go">
    <div class="badge">📍 下一步</div>
    <div class="body">
      <div class="ico">{{ step.icon }}</div>
      <div class="txt">
        <div class="title">{{ step.title }}</div>
        <div class="desc">{{ step.desc }}</div>
      </div>
    </div>
    <div class="cta">{{ step.cta }} <span class="arrow">→</span></div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { NextStep } from '@/lib/nextStep'
const props = defineProps<{ step: NextStep }>()
const router = useRouter()
function go() { router.push(props.step.to) }
</script>

<style scoped>
.next {
  position: relative; cursor: pointer; overflow: hidden;
  background: var(--grad-brand); color: #fff; border-radius: var(--r-xl);
  padding: var(--sp-6); box-shadow: var(--sh-brand); transition: transform .2s;
}
.next:hover { transform: translateY(-3px); }
.badge { font-size: var(--fz-2); font-weight: 700; opacity: .85; }
.body { display: flex; align-items: center; gap: var(--sp-4); margin: var(--sp-3) 0 var(--sp-5); }
.ico { font-size: 38px; flex-shrink: 0; }
.title { font-size: var(--fz-6); font-weight: 800; }
.desc { font-size: var(--fz-3); opacity: .92; margin-top: 4px; }
.cta {
  display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.2);
  padding: 9px 18px; border-radius: var(--r-full); font-weight: 700; font-size: var(--fz-3);
}
.arrow { transition: transform .2s; }
.next:hover .arrow { transform: translateX(4px); }
</style>
