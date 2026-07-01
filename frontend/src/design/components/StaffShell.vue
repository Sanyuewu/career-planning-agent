<template>
  <div class="shell">
    <header class="topbar">
      <div class="bar-inner">
        <div class="brand" @click="router.push('/staff/dashboard')">
          <span class="logo">🎓</span><span class="bname">职途</span><span class="tag">院校端</span>
        </div>
        <nav class="nav">
          <RouterLink v-for="n in nav" :key="n.to" :to="n.to" class="nav-item">
            <span class="ico">{{ n.icon }}</span>{{ n.label }}
          </RouterLink>
        </nav>
        <div class="user">
          <span class="uname u-ellipsis">{{ session.displayName }} · {{ roleLabel }}</span>
          <button class="logout" @click="onLogout">退出</button>
        </div>
      </div>
    </header>
    <main class="content"><slot /></main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSession } from '@/stores/session'

const router = useRouter()
const session = useSession()

const nav = computed(() => {
  const items = [{ to: '/staff/dashboard', label: '看板', icon: '📊' }]
  if (session.role === 'admin') {
    items.push({ to: '/staff/manage', label: '管理', icon: '🏫' })
    items.push({ to: '/staff/config', label: '配置', icon: '⚙️' })
  }
  return items
})
const roleLabel = computed(() => session.role === 'admin' ? '管理员' : session.role === 'teacher' ? '教师' : '')

function onLogout() {
  session.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell { min-height: 100vh; }
.topbar { position: fixed; top: 0; left: 0; right: 0; z-index: 100; height: var(--topbar-h);
  background: rgba(255,255,255,0.85); backdrop-filter: blur(12px); border-bottom: 1px solid var(--c-border); }
.bar-inner { max-width: 1140px; margin: 0 auto; height: 100%; display: flex; align-items: center;
  gap: var(--sp-8); padding: 0 var(--sp-5); }
.brand { display: flex; align-items: center; gap: var(--sp-2); cursor: pointer; flex-shrink: 0; }
.logo { font-size: 22px; }
.bname { font-size: var(--fz-4); font-weight: 800; background: var(--grad-brand);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.tag { font-size: var(--fz-1); font-weight: 700; color: var(--c-growth); background: var(--c-growth-weak);
  padding: 2px 8px; border-radius: var(--r-full); }
.nav { display: flex; gap: var(--sp-1); flex: 1; }
.nav-item { display: flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: var(--r-md);
  font-size: var(--fz-3); font-weight: 600; color: var(--c-text-2); transition: all .18s; }
.nav-item:hover, .nav-item.router-link-active { background: var(--c-primary-weak); color: var(--c-primary); }
.user { display: flex; align-items: center; gap: var(--sp-3); flex-shrink: 0; }
.uname { font-size: var(--fz-3); color: var(--c-text); max-width: 160px; }
.logout { border: 1px solid var(--c-border-2); background: none; border-radius: var(--r-sm);
  padding: 5px 12px; font-size: var(--fz-2); color: var(--c-text-2); cursor: pointer; transition: all .18s; }
.logout:hover { border-color: var(--c-danger); color: var(--c-danger); }
.content { max-width: 1140px; margin: 0 auto; padding: calc(var(--topbar-h) + var(--sp-6)) var(--sp-5) var(--sp-12); }
@media (max-width: 720px) { .bar-inner { gap: var(--sp-4); } .nav-item .ico { display: none; } .uname { display: none; } }
</style>
