<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <div class="navbar-logo" @click="goHome">
        <span class="logo-icon">🎓</span>
        <span class="logo-text">职业规划智能体</span>
      </div>

      <div class="navbar-links">
        <router-link to="/home" class="nav-link">首页</router-link>
        <!-- 学生导航 -->
        <template v-if="userStore.isLoggedIn && userStore.isStudent">
          <router-link to="/upload" class="nav-link">简历</router-link>
          <router-link to="/portrait" class="nav-link" v-if="userStore.studentId">画像</router-link>
          <router-link to="/match" class="nav-link" v-if="userStore.studentId">匹配</router-link>
          <router-link to="/report" class="nav-link" v-if="userStore.studentId">报告</router-link>
          <!-- 测评页暂时隐藏
          <router-link to="/assessment" class="nav-link" v-if="userStore.studentId">测评</router-link>
          -->
          <router-link to="/chat" class="nav-link">AI对话</router-link>
        </template>
        <!-- 企业导航 -->
        <template v-else-if="userStore.isLoggedIn && userStore.isCompany">
          <router-link to="/company" class="nav-link nav-link-company">工作台</router-link>
        </template>
        <!-- 管理员导航 -->
        <template v-else-if="userStore.isLoggedIn && userStore.isAdmin">
          <router-link to="/admin" class="nav-link nav-link-admin">管理后台</router-link>
        </template>
        <!-- 未登录 -->
        <template v-else>
          <router-link to="/chat" class="nav-link">AI对话</router-link>
        </template>
      </div>

      <!-- 继续上次工作入口 -->
      <div class="continue-work" v-if="lastVisitedPage && userStore.isLoggedIn">
        <button class="continue-btn" @click="continueLastWork">
          <span class="continue-icon">📍</span>
          <span class="continue-text">继续上次</span>
        </button>
      </div>

      <div class="navbar-user" v-if="userStore.isLoggedIn">
        <div class="user-badge">
          <span class="role-tag" :class="roleClass">{{ roleLabel }}</span>
          <span class="user-name">{{ userStore.userName }}</span>
        </div>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
      
      <div class="navbar-auth" v-else>
        <router-link to="/login" class="login-link">登录</router-link>
        <router-link to="/login" class="register-btn">注册</router-link>
      </div>

      <!-- 暗色主题切换按钮暂时隐藏
      <button class="theme-toggle-btn" @click="toggleTheme" :title="isDark ? '切换亮色' : '切换暗色'">
        {{ isDark ? '☀️' : '🌙' }}
      </button>
      -->
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/useUserStore'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const LAST_VISITED_KEY = 'last_visited_page'
const EXCLUDED_PATHS = ['/login', '/home', '/']

const lastVisitedPage = computed(() => {
  const saved = localStorage.getItem(LAST_VISITED_KEY)
  if (!saved) return null
  try {
    const data = JSON.parse(saved)
    if (Date.now() - data.timestamp > 7 * 24 * 60 * 60 * 1000) return null
    return data.path
  } catch {
    return null
  }
})

const roleLabel = computed(() => {
  if (userStore.isAdmin) return '管理员'
  if (userStore.isCompany) return '企业'
  return '学生'
})

const roleClass = computed(() => {
  if (userStore.isAdmin) return 'role-admin'
  if (userStore.isCompany) return 'role-company'
  return 'role-student'
})

function saveLastVisited(path: string) {
  if (EXCLUDED_PATHS.some(p => path.startsWith(p))) return
  localStorage.setItem(LAST_VISITED_KEY, JSON.stringify({
    path,
    timestamp: Date.now()
  }))
}

function continueLastWork() {
  const path = lastVisitedPage.value
  if (path) {
    router.push(path)
  }
}

function goHome() {
  router.push('/home')
}

function handleLogout() {
  userStore.logout()
  localStorage.removeItem(LAST_VISITED_KEY)
  router.push('/home')
}

watch(() => route.path, (path) => {
  if (path && userStore.isLoggedIn) {
    saveLastVisited(path)
  }
}, { immediate: true })

// 暗色主题（暂时隐藏切换按钮，保留初始化逻辑）
const isDark = ref(localStorage.getItem('theme') === 'dark')

function applyTheme(dark: boolean) {
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
  localStorage.setItem('theme', dark ? 'dark' : 'light')
}

// function toggleTheme() {
//   isDark.value = !isDark.value
//   applyTheme(isDark.value)
// }

onMounted(() => {
  if (route.path && userStore.isLoggedIn) {
    saveLastVisited(route.path)
  }
  // 初始化主题
  applyTheme(isDark.value)
})
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 900;
  height: 56px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.navbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 32px;
}

.navbar-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex-shrink: 0;
}

.logo-icon {
  font-size: 22px;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.navbar-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #555;
  text-decoration: none;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #f0f4ff;
  color: #667eea;
}

.nav-link.router-link-active {
  background: #f0f4ff;
  color: #667eea;
  font-weight: 600;
}

.nav-link-company {
  color: #52c41a;
  font-weight: 600;
}
.nav-link-company:hover,
.nav-link-company.router-link-active {
  background: #f0ffe8;
  color: #389e0d;
}

.nav-link-admin {
  color: #fa8c16;
  font-weight: 600;
}
.nav-link-admin:hover,
.nav-link-admin.router-link-active {
  background: #fff7e6;
  color: #d46b08;
}

.navbar-user {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-tag {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.role-student {
  background: #e8f4ff;
  color: #1890ff;
}

.role-company {
  background: #f0ffe8;
  color: #52c41a;
}

.role-admin {
  background: #fff7e6;
  color: #fa8c16;
}

.user-name {
  font-size: 14px;
  color: #333;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  padding: 5px 14px;
  border: 1.5px solid #e0e0e0;
  border-radius: 8px;
  background: none;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  border-color: #ff4d4f;
  color: #ff4d4f;
}

.navbar-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.login-link {
  font-size: 14px;
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.login-link:hover {
  color: #764ba2;
}

.register-btn {
  padding: 6px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.register-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.continue-work {
  flex-shrink: 0;
}

.continue-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1.5px solid #667eea;
  border-radius: 8px;
  background: #f0f4ff;
  color: #667eea;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.continue-btn:hover {
  background: #667eea;
  color: white;
}

.continue-icon {
  font-size: 14px;
}

.continue-text {
  font-size: 13px;
}

@media (max-width: 768px) {
  .navbar-inner {
    padding: 0 16px;
    gap: 16px;
  }
  
  .navbar-links {
    display: none;
  }
  
  .continue-work {
    display: none;
  }
  
  .user-name {
    max-width: 80px;
  }
}

/* E-3: 主题切换按钮 */
.theme-toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
  margin-left: 4px;
}
.theme-toggle-btn:hover {
  background: rgba(0,0,0,0.06);
}
</style>
