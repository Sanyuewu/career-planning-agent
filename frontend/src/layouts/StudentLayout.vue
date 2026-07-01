<template>
  <AppShell>
    <RouterView v-slot="{ Component }">
      <component :is="Component" class="fade-up" />
    </RouterView>
  </AppShell>
</template>

<script setup lang="ts">
import AppShell from '@/design/components/AppShell.vue'
</script>
