import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useSession } from '@/stores/session'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  { path: '/login', name: 'login', component: () => import('@/features/auth/LoginView.vue'), meta: { title: '登录' } },
  {
    path: '/',
    component: () => import('@/layouts/StudentLayout.vue'),
    meta: { auth: true },
    children: [
      { path: 'home', name: 'home', component: () => import('@/features/home/HomeView.vue'), meta: { title: '主页' } },
      { path: 'growth', name: 'growth', component: () => import('@/features/growth/GrowthView.vue'), meta: { title: '我的成长' } },
      { path: 'advisor', name: 'advisor', component: () => import('@/features/advisor/AdvisorView.vue'), meta: { title: 'AI 顾问' } },
      { path: 'jobs', name: 'jobs', component: () => import('@/features/jobs/JobsView.vue'), meta: { title: '岗位探索' } },
      { path: 'jobs/:title', name: 'jobDetail', component: () => import('@/features/jobs/JobDetailView.vue'), meta: { title: '岗位详情' } },
      { path: 'journey/upload', name: 'upload', component: () => import('@/features/journey/UploadView.vue'), meta: { title: '上传简历' } },
      { path: 'journey/portrait', name: 'portrait', component: () => import('@/features/journey/PortraitView.vue'), meta: { title: '我的画像' } },
      { path: 'journey/match', name: 'match', component: () => import('@/features/journey/MatchView.vue'), meta: { title: '人岗匹配' } },
      { path: 'journey/report', name: 'report', component: () => import('@/features/journey/ReportView.vue'), meta: { title: '职业报告' } },
    ],
  },
  {
    path: '/staff',
    component: () => import('@/layouts/StaffLayout.vue'),
    meta: { auth: true, staff: true },
    children: [
      { path: '', redirect: '/staff/dashboard' },
      { path: 'dashboard', name: 'staffDashboard', component: () => import('@/features/staff/DashboardView.vue'), meta: { title: '院校看板' } },
      { path: 'manage', name: 'staffManage', component: () => import('@/features/staff/ManageView.vue'), meta: { title: '组织管理', adminOnly: true } },
      { path: 'config', name: 'staffConfig', component: () => import('@/features/staff/ConfigView.vue'), meta: { title: '院校配置', adminOnly: true } },
    ],
  },
  {
    path: '/platform',
    component: () => import('@/layouts/PlatformLayout.vue'),
    meta: { auth: true, platform: true },
    children: [
      { path: '', redirect: '/platform/overview' },
      { path: 'overview', name: 'platformOverview', component: () => import('@/features/platform/OverviewView.vue'), meta: { title: '平台总览' } },
      { path: 'tenants', name: 'platformTenants', component: () => import('@/features/platform/TenantsView.vue'), meta: { title: '租户管理' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({ history: createWebHistory(), routes })

// 各角色的"家区"
function homeArea(session: ReturnType<typeof useSession>): string {
  if (session.isPlatform) return '/platform/overview'
  if (session.isStaff) return '/staff/dashboard'
  return '/home'
}

router.beforeEach((to) => {
  document.title = `${to.meta.title || '职途'} · 职途`
  const session = useSession()

  if (to.meta.auth && !session.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!session.isLoggedIn) return true

  // 四角色分流：每个角色只能待在自己的家区，越界回家
  const inPlatform = to.path.startsWith('/platform')
  const inStaff = to.path.startsWith('/staff')
  const myArea = homeArea(session)

  if (session.isPlatform && !inPlatform) return { path: myArea }
  if (session.isStaff && !inStaff) return { path: myArea }
  if (session.isStudent && (inPlatform || inStaff)) return { path: '/home' }
  // 非超管不得入平台区；非教职工不得入院校区
  if (inPlatform && !session.isPlatform) return { path: myArea }
  if (inStaff && !session.isStaff) return { path: myArea }
  // admin-only 页（管理/配置）：教师挡回看板
  if (to.meta.adminOnly && session.role !== 'admin') return { path: '/staff/dashboard' }
  return true
})

export default router
