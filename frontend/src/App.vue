<template>
  <a-config-provider>
    <NavBar v-if="showNavBar" />
    <FlowStepBar v-if="showFlowBar" />
    <div :style="showNavBar ? 'padding-top: 56px' : ''">
      <ErrorBoundary>
        <router-view />
      </ErrorBoundary>
    </div>
    <div class="offline-bar" v-if="isOffline">
      <span>网络已断开，请检查网络连接</span>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from './stores/useUserStore'
import NavBar from './components/NavBar.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'
import FlowStepBar from './components/FlowStepBar.vue'

const isOffline = ref(!navigator.onLine)
const userStore = useUserStore()
const route = useRoute()

// 仅在已登录且非 home/login 页面时显示导航栏
const showNavBar = computed(() => {
  const noNavRoutes = ['/', '/home', '/login']
  return userStore.isLoggedIn && !noNavRoutes.includes(route.path)
})

// 核心流程五页面显示步骤条
const FLOW_PATHS = ['/upload', '/portrait', '/match', '/chat', '/report']
const showFlowBar = computed(() =>
  userStore.isLoggedIn && FLOW_PATHS.some(p => route.path.startsWith(p))
)

function handleOnline() { isOffline.value = false }
function handleOffline() { isOffline.value = true }

function reportClientError(message: string, url: string = location.href) {
  const traceId = localStorage.getItem('last_trace_id') || ''
  fetch('/api/debug/client-error', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, url, traceId }),
  }).catch((e) => { console.warn('客户端错误上报失败:', e) })
}

onMounted(() => {
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)

  // 静默验证localStorage中的student_id是否仍有效（防止后端重启后数据丢失导致错误状态）
  userStore.validateStudent()

  // 全局未捕获异常 → 上报到后端监控
  window.addEventListener('error', (event) => {
    reportClientError(`${event.message} @ ${event.filename}:${event.lineno}`)
  })
  window.addEventListener('unhandledrejection', (event) => {
    reportClientError(`UnhandledPromiseRejection: ${event.reason?.message || event.reason}`)
  })
})
onUnmounted(() => {
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
})
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

#app {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.offline-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: #ff4d4f;
  color: #fff;
  text-align: center;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
</style>
