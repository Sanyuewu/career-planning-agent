<template>
  <div v-if="showHint" class="guest-limit-hint" :class="type">
    <div class="hint-icon">{{ iconMap[type] }}</div>
    <div class="hint-content">
      <p class="hint-title">{{ titleMap[type] }}</p>
      <p class="hint-desc">{{ descMap[type] }}</p>
    </div>
    <button class="hint-action" @click="handleLogin">
      {{ actionMap[type] }}
    </button>
    <button class="hint-close" @click="dismiss" aria-label="关闭提示">×</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '../stores/useUserStore'

const props = defineProps<{
  type: 'match' | 'report' | 'portrait' | 'chat'
}>()

const emit = defineEmits<{
  login: []
}>()

const userStore = useUserStore()
const dismissed = ref(false)

const iconMap: Record<string, string> = {
  match: '📊',
  report: '📄',
  portrait: '👤',
  chat: '💬'
}

const titleMap: Record<string, string> = {
  match: '游客模式限制',
  report: '导出功能受限',
  portrait: '编辑功能受限',
  chat: '历史记录受限'
}

const descMap: Record<string, string> = {
  match: '登录后可保存匹配历史，随时查看对比',
  report: '登录后可导出PDF/Word格式的完整报告',
  portrait: '登录后可编辑个人资料和技能信息',
  chat: '登录后可保存对话历史，随时回顾'
}

const actionMap: Record<string, string> = {
  match: '登录保存',
  report: '登录导出',
  portrait: '登录编辑',
  chat: '登录保存'
}

const showHint = computed(() => {
  return !userStore.isLoggedIn && !dismissed.value
})

const storageKey = computed(() => `guest_hint_dismissed_${props.type}`)

onMounted(() => {
  const saved = localStorage.getItem(storageKey.value)
  if (saved === 'true') {
    dismissed.value = true
  }
})

function dismiss() {
  dismissed.value = true
  localStorage.setItem(storageKey.value, 'true')
}

function handleLogin() {
  emit('login')
}
</script>

<style scoped>
.guest-limit-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #fff7e6 0%, #fff1cc 100%);
  border: 1px solid #ffd591;
  border-radius: 12px;
  margin-bottom: 16px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.guest-limit-hint.match {
  background: linear-gradient(135deg, #e6f7ff 0%, #d6f0ff 100%);
  border-color: #91d5ff;
}

.guest-limit-hint.report {
  background: linear-gradient(135deg, #f6ffed 0%, #e6ffdb 100%);
  border-color: #b7eb8f;
}

.guest-limit-hint.portrait {
  background: linear-gradient(135deg, #fff0f6 0%, #ffe6ef 100%);
  border-color: #ffa0c0;
}

.guest-limit-hint.chat {
  background: linear-gradient(135deg, #f0f5ff 0%, #e0e8ff 100%);
  border-color: #adc6ff;
}

.hint-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.hint-content {
  flex: 1;
  min-width: 0;
}

.hint-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 2px;
}

.hint-desc {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.hint-action {
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.hint-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.hint-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  flex-shrink: 0;
}

.hint-close:hover {
  color: #666;
}

@media (max-width: 640px) {
  .guest-limit-hint {
    flex-wrap: wrap;
    padding: 12px;
  }

  .hint-content {
    order: 1;
    width: calc(100% - 40px);
  }

  .hint-icon {
    order: 0;
  }

  .hint-action {
    order: 3;
    width: 100%;
    margin-top: 8px;
  }

  .hint-close {
    order: 2;
    position: absolute;
    right: 8px;
    top: 8px;
  }

  .guest-limit-hint {
    position: relative;
  }
}
</style>
