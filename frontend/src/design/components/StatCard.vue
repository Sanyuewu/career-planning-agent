<template>
  <div class="stat">
    <div class="label u-muted">{{ label }}</div>
    <div class="value">{{ value }}<span v-if="unit" class="unit">{{ unit }}</span></div>
    <div class="delta" :class="deltaClass">
      <slot name="delta">{{ deltaText }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ label: string; value: string | number; unit?: string; delta?: number | null; deltaText?: string }>()
const deltaClass = computed(() => {
  if (props.delta === null || props.delta === undefined) return ''
  return props.delta > 0 ? 'u-up' : props.delta < 0 ? 'u-down' : ''
})
</script>

<style scoped>
.stat {
  background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--r-lg);
  padding: var(--sp-5); box-shadow: var(--sh-sm);
}
.label { font-size: var(--fz-2); }
.value { font-size: var(--fz-7); font-weight: 800; line-height: 1.1; margin: 6px 0 4px; }
.unit { font-size: var(--fz-4); font-weight: 700; color: var(--c-text-2); margin-left: 3px; }
.delta { font-size: var(--fz-2); color: var(--c-text-3); min-height: 18px; }
</style>
