<template>
  <div class="sec-title">
    <div class="left">
      <h3>{{ title }}</h3>
      <p v-if="sub" class="sub u-muted">{{ sub }}</p>
    </div>
    <div class="right"><slot name="action" /></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; sub?: string }>()
</script>

<style scoped>
.sec-title { display: flex; align-items: flex-end; justify-content: space-between; margin: 0 0 var(--sp-4); }
h3 { font-size: var(--fz-5); font-weight: 800; }
.sub { font-size: var(--fz-2); margin-top: 2px; }
</style>
