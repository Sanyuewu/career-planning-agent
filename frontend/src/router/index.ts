import { createRouter, createWebHistory, type RouteLocationNormalized, type NavigationGuardNext } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/jobs/:jobId',
    name: 'JobDetail',
    component: () => import('../views/JobDetail.vue'),
    meta: { title: '岗位详情' },
  },
  {
    path: '/upload',
    name: 'ResumeUpload',
    component: () => import('../views/ResumeUpload.vue'),
    meta: { title: '简历上传', requiresStudent: true },
  },
  {
    path: '/portrait',
    name: 'Portrait',
    component: () => import('../views/Portrait.vue'),
    meta: { title: '学生画像', requiresAuth: true, requiresStudent: true },
  },
  {
    path: '/match',
    name: 'MatchAnalysis',
    component: () => import('../views/MatchAnalysis.vue'),
    meta: { title: '人岗匹配', requiresAuth: true, requiresStudent: true },
  },
  {
    path: '/report',
    name: 'CareerReport',
    component: () => import('../views/CareerReport.vue'),
    meta: { title: '职业报告', requiresAuth: true, requiresStudent: true },
  },
  {
    path: '/graph/:jobId?',
    name: 'CareerGraph',
    component: () => import('../views/CareerGraph.vue'),
    meta: { title: '职业图谱' },
  },
  {
    path: '/chat',
    name: 'ChatAdvisor',
    component: () => import('../views/ChatAdvisor.vue'),
    meta: { title: 'AI对话' },
  },
  // 测评页暂时隐藏
  // {
  //   path: '/assessment',
  //   name: 'Assessment',
  //   component: () => import('../views/Assessment.vue'),
  //   meta: { title: '能力测评' },
  // },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录/注册' },
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('../views/AdminDashboard.vue'),
    meta: { title: '管理后台', requiresRole: 'admin' },
  },
  {
    path: '/company',
    name: 'CompanyDashboard',
    component: () => import('../views/CompanyDashboard.vue'),
    meta: { title: '企业端', requiresRole: 'company' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
  document.title = `${to.meta.title || '职业规划'} - 职业规划智能体`

  const { useUserStore } = await import('../stores/useUserStore')
  const userStore = useUserStore()

  // 学生专属路由：企业/管理员直接跳转到自己的工作台
  if (to.meta.requiresStudent) {
    if (userStore.isLoggedIn) {
      if (userStore.isCompany) {
        next('/company')
        return
      }
      if (userStore.isAdmin) {
        next('/admin')
        return
      }
    }
  }

  if (to.meta.requiresRole) {
    if (!userStore.accessToken) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
    if (userStore.role !== to.meta.requiresRole) {
      next('/home')
      return
    }
  }

  if (to.meta.requiresAuth) {
    // Token 过期时主动登出，避免进入页面后出现静默的 401 失败
    if (userStore.isLoggedIn && userStore.accessToken && userStore.isTokenExpired()) {
      userStore.logout()
      next({ path: '/login', query: { redirect: to.fullPath, reason: 'expired' } })
      return
    }
    if (!userStore.isLoggedIn) {
      next({
        path: '/login',
        query: { redirect: to.fullPath },
      })
      return
    }
    if (!userStore.studentId) {
      next({
        path: '/upload',
        query: { redirect: to.fullPath },
      })
      return
    }
  }

  next()
})

export default router
