<template>
  <PlatformShell>
    <RouterView v-slot="{ Component }">
      <component :is="Component" class="fade-up" />
    </RouterView>
  </PlatformShell>
</template>

<script setup lang="ts">
import PlatformShell from '@/design/components/PlatformShell.vue'
</script>
