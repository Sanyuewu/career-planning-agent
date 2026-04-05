<template>
  <div class="empty-state" :class="size">
    <div class="empty-icon">{{ displayIcon }}</div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc" v-if="description">{{ description }}</p>
    <slot name="action">
      <button 
        class="empty-action" 
        v-if="actionText" 
        @click="$emit('action')"
      >
        {{ actionText }}
      </button>
    </slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  icon?: string
  title: string
  description?: string
  actionText?: string
  size?: 'small' | 'medium' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium'
})

defineEmits<{
  action: []
}>()

const defaultIcons: Record<string, string> = {
  data: '📊',
  search: '🔍',
  error: '❌',
  empty: '📭',
  network: '🌐',
  permission: '🔒'
}

const displayIcon = computed(() => {
  return props.icon || defaultIcons.empty
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-state.small {
  padding: 20px 16px;
}

.empty-state.small .empty-icon {
  font-size: 40px;
}

.empty-state.small .empty-title {
  font-size: 14px;
}

.empty-state.small .empty-desc {
  font-size: 12px;
}

.empty-state.large {
  padding: 60px 30px;
}

.empty-state.large .empty-icon {
  font-size: 80px;
}

.empty-state.large .empty-title {
  font-size: 20px;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 16px;
  opacity: 0.8;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 14px;
  color: #999;
  margin: 0 0 20px;
  max-width: 300px;
  line-height: 1.5;
}

.empty-action {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.empty-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}
</style>
