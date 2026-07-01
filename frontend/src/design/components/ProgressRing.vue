<template>
  <div class="ring" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <defs>
        <linearGradient :id="gid" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#6d5efc" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </linearGradient>
      </defs>
      <circle :cx="c" :cy="c" :r="r" :stroke-width="stroke" class="track" fill="none" />
      <circle :cx="c" :cy="c" :r="r" :stroke-width="stroke" fill="none" :stroke="`url(#${gid})`"
        stroke-linecap="round" :stroke-dasharray="circ" :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${c} ${c})`" style="transition: stroke-dashoffset .8s ease" />
    </svg>
    <div class="center">
      <div class="val">{{ Math.round(value) }}</div>
      <div v-if="label" class="lbl u-faint">{{ label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{ value: number; size?: number; stroke?: number; label?: string }>(),
  { size: 120, stroke: 10, label: '' })
const gid = `ring-${Math.random().toString(36).slice(2, 8)}`
const c = computed(() => props.size / 2)
const r = computed(() => props.size / 2 - props.stroke)
const circ = computed(() => 2 * Math.PI * r.value)
const offset = computed(() => circ.value * (1 - Math.max(0, Math.min(100, props.value)) / 100))
</script>

<style scoped>
.ring { position: relative; display: inline-block; }
.track { stroke: var(--c-border); }
.center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.val { font-size: var(--fz-6); font-weight: 800; color: var(--c-text); }
.lbl { font-size: var(--fz-1); }
</style>
