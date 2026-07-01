<template>
  <div class="auth">
    <div class="auth-card fade-up">
      <div class="brand"><span class="logo">🎓</span><span class="bn">职途</span></div>
      <p class="tagline">看见自己在变好</p>

      <div class="tabs">
        <button :class="{ on: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ on: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <a-input v-model="username" placeholder="用户名" size="large" class="fld" allow-clear />
      <a-input-password v-model="password" placeholder="密码" size="large" class="fld" @keyup.enter="submit" />

      <AppButton block size="lg" :loading="loading" @click="submit">
        {{ mode === 'login' ? '登录' : '注册并开始' }}
      </AppButton>
      <p class="hint u-faint">{{ mode === 'login' ? '没有账号？点上方「注册」' : '注册即创建你的学生档案' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import AppButton from '@/design/components/AppButton.vue'
import { useSession } from '@/stores/session'

const router = useRouter()
const route = useRoute()
const session = useSession()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) { Message.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    if (mode.value === 'login') await session.login(username.value, password.value)
    else await session.register(username.value, password.value)
    Message.success(mode.value === 'login' ? '欢迎回来' : '账号已创建')
    const redirect = (route.query.redirect as string) || '/home'
    router.replace(redirect)
  } catch { /* http 层已弹错误 */ } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: var(--grad-brand-soft); padding: var(--sp-4); }
.auth-card { width: 380px; max-width: 100%; background: var(--c-surface); border-radius: var(--r-xl);
  box-shadow: var(--sh-lg); padding: var(--sp-10) var(--sp-8); }
.brand { display: flex; align-items: center; justify-content: center; gap: var(--sp-2); }
.logo { font-size: 30px; }
.bn { font-size: var(--fz-6); font-weight: 800; background: var(--grad-brand);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.tagline { text-align: center; color: var(--c-text-2); margin: 6px 0 var(--sp-6); }
.tabs { display: flex; background: var(--c-bg); border-radius: var(--r-md); padding: 4px; margin-bottom: var(--sp-5); }
.tabs button { flex: 1; border: none; background: none; padding: 9px; border-radius: var(--r-sm);
  font-weight: 700; color: var(--c-text-2); cursor: pointer; transition: all .18s; }
.tabs button.on { background: var(--c-surface); color: var(--c-primary); box-shadow: var(--sh-sm); }
.fld { margin-bottom: var(--sp-4); }
.hint { text-align: center; margin-top: var(--sp-4); font-size: var(--fz-2); }
</style>
