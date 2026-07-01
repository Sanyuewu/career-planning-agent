<template>
  <div class="empty">
    <div class="icon">{{ icon }}</div>
    <p class="text">{{ text }}</p>
    <div class="action"><slot /></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ icon?: string; text?: string }>(), { icon: '🌱', text: '暂无数据' })
</script>

<style scoped>
.empty { display: flex; flex-direction: column; align-items: center; gap: var(--sp-3); padding: var(--sp-10) var(--sp-4); text-align: center; }
.icon { font-size: 40px; opacity: .9; }
.text { color: var(--c-text-2); font-size: var(--fz-3); max-width: 340px; }
.action { margin-top: var(--sp-2); }
</style>
