<template>
  <button class="btn" :class="[`v-${variant}`, `s-${size}`, { block, loading }]"
          :disabled="disabled || loading" @click="$emit('click', $event)">
    <span v-if="loading" class="spin"></span>
    <slot />
  </button>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'primary' | 'ghost' | 'soft'
  size?: 'sm' | 'md' | 'lg'
  block?: boolean
  loading?: boolean
  disabled?: boolean
}>(), { variant: 'primary', size: 'md', block: false, loading: false, disabled: false })
defineEmits<{ (e: 'click', ev: MouseEvent): void }>()
</script>

<style scoped>
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  border: none; border-radius: var(--r-md); font-weight: 700; cursor: pointer;
  transition: all .18s; white-space: nowrap;
}
.btn:disabled { opacity: .55; cursor: not-allowed; }
.s-sm { padding: 6px 14px; font-size: var(--fz-2); }
.s-md { padding: 10px 20px; font-size: var(--fz-3); }
.s-lg { padding: 14px 28px; font-size: var(--fz-4); }
.block { width: 100%; }
.v-primary { background: var(--grad-brand); color: #fff; box-shadow: var(--sh-brand); }
.v-primary:not(:disabled):hover { transform: translateY(-1px); filter: brightness(1.05); }
.v-soft { background: var(--c-primary-weak); color: var(--c-primary); }
.v-soft:not(:disabled):hover { background: #e4e0ff; }
.v-ghost { background: transparent; color: var(--c-text-2); border: 1px solid var(--c-border-2); }
.v-ghost:not(:disabled):hover { border-color: var(--c-primary); color: var(--c-primary); }
.spin { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent;
  border-radius: 50%; animation: btnspin .7s linear infinite; }
@keyframes btnspin { to { transform: rotate(360deg); } }
</style>
