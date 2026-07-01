<template>
  <div class="coming">
    <div class="emoji">🚧</div>
    <h2>{{ title }}</h2>
    <p class="u-muted">此模块正在重做中，很快上线</p>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
const title = (route.meta.title as string) || '建设中'
</script>

<style scoped>
.coming { text-align: center; padding: var(--sp-12) var(--sp-4); }
.emoji { font-size: 52px; }
h2 { font-size: var(--fz-6); margin: var(--sp-3) 0 var(--sp-2); }
</style>
