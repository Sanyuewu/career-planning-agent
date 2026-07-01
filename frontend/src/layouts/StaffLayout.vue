<template>
  <StaffShell>
    <RouterView v-slot="{ Component }">
      <component :is="Component" class="fade-up" />
    </RouterView>
  </StaffShell>
</template>

<script setup lang="ts">
import StaffShell from '@/design/components/StaffShell.vue'
</script>
