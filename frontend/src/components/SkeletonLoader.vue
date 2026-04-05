<template>
  <div class="skeleton-wrapper" :class="{ 'full-width': fullWidth }">
    <div v-if="type === 'card'" class="skeleton-card">
      <div class="skel skel-title" :style="{ width: titleWidth }"></div>
      <div class="skel skel-text" v-for="i in rows" :key="i" :style="{ width: getRowWidth(i) }"></div>
    </div>
    
    <div v-else-if="type === 'list'" class="skeleton-list">
      <div class="skeleton-list-item" v-for="i in rows" :key="i">
        <div class="skel skel-avatar" v-if="showAvatar"></div>
        <div class="skeleton-list-content">
          <div class="skel skel-text short"></div>
          <div class="skel skel-text shorter"></div>
        </div>
      </div>
    </div>
    
    <div v-else-if="type === 'tags'" class="skeleton-tags">
      <div class="skel skel-tag" v-for="i in rows" :key="i"></div>
    </div>
    
    <div v-else-if="type === 'score'" class="skeleton-score">
      <div class="skel skel-circle"></div>
      <div class="skeleton-score-bars">
        <div class="skel skel-bar" v-for="i in rows" :key="i"></div>
      </div>
    </div>
    
    <div v-else-if="type === 'radar'" class="skeleton-radar">
      <div class="skel skel-radar-shape"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  type?: 'card' | 'list' | 'tags' | 'score' | 'radar'
  rows?: number
  titleWidth?: string
  showAvatar?: boolean
  fullWidth?: boolean
}>()

function getRowWidth(index: number): string {
  const widths = ['80%', '100%', '90%', '75%', '85%', '70%']
  return widths[index % widths.length]
}
</script>

<style scoped>
.skeleton-wrapper {
  width: 100%;
}

.skeleton-wrapper.full-width {
  width: 100%;
}

@keyframes shimmer {
  0% { background-position: -468px 0; }
  100% { background-position: 468px 0; }
}

.skel {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 468px 100%;
  animation: shimmer 1.2s ease-in-out infinite;
  border-radius: 6px;
}

.skeleton-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skel-title {
  height: 20px;
  width: 40%;
  margin-bottom: 4px;
}

.skel-text {
  height: 14px;
  width: 100%;
}

.skel-text.short { width: 70%; }
.skel-text.shorter { width: 50%; }

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 10px;
}

.skel-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skel-tag {
  height: 28px;
  width: 80px;
  border-radius: 14px;
}

.skeleton-score {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 20px;
}

.skel-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-score-bars {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skel-bar {
  height: 12px;
  width: 100%;
  border-radius: 6px;
}

.skeleton-radar {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.skel-radar-shape {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  transform: rotate(30deg);
}
</style>
