<template>
  <div class="error-boundary" v-if="hasError">
    <div class="error-content">
      <div class="error-icon">{{ icon }}</div>
      <h3 class="error-title">{{ title }}</h3>
      <p class="error-message">{{ message }}</p>
      <div class="error-actions">
        <button class="retry-btn" @click="handleRetry" v-if="showRetry">
          {{ retryText }}
        </button>
        <button class="back-btn" @click="handleBack" v-if="showBack">
          返回上一页
        </button>
      </div>
      <div class="error-details" v-if="showDetails && errorDetail">
        <details>
          <summary>详细信息</summary>
          <pre>{{ errorDetail }}</pre>
        </details>
      </div>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const props = withDefaults(defineProps<{
  title?: string
  message?: string
  icon?: string
  showRetry?: boolean
  showBack?: boolean
  showDetails?: boolean
  retryText?: string
}>(), {
  title: '加载失败',
  message: '页面加载时发生错误，请稍后重试',
  icon: '⚠️',
  showRetry: true,
  showBack: true,
  showDetails: false,
  retryText: '重新加载',
})

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()
const hasError = ref(false)
const errorDetail = ref('')

onErrorCaptured((err: Error) => {
  hasError.value = true
  errorDetail.value = err.message || String(err)
  console.error('ErrorBoundary captured:', err)
  return false
})

function handleRetry() {
  hasError.value = false
  errorDetail.value = ''
  emit('retry')
}

function handleBack() {
  router.back()
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 40px 20px;
}

.error-content {
  text-align: center;
  max-width: 400px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.error-message {
  font-size: 14px;
  color: #666;
  margin: 0 0 20px;
  line-height: 1.6;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.retry-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  transition: all 0.2s;
}

.retry-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.back-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  background: white;
  color: #667eea;
  border: 1px solid #667eea;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #f8f9ff;
}

.error-details {
  margin-top: 20px;
  text-align: left;
}

.error-details summary {
  font-size: 13px;
  color: #999;
  cursor: pointer;
}

.error-details pre {
  margin-top: 8px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
