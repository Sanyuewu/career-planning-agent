<template>
  <section class="card" :class="{ pad, hover }">
    <slot />
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ pad?: boolean; hover?: boolean }>(), { pad: true, hover: false })
</script>

<style scoped>
.card {
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--r-lg); box-shadow: var(--sh-sm); transition: box-shadow .2s, transform .2s;
}
.card.pad { padding: var(--sp-6); }
.card.hover:hover { box-shadow: var(--sh-md); transform: translateY(-2px); }
</style>
