<template>
  <div class="login-modal-overlay" @click.self="$emit('close')">
    <div class="login-modal">
      <button class="close-btn" @click="$emit('close')">×</button>
      
      <div class="modal-header">
        <h2>{{ isRegister ? '注册账号' : '登录' }}</h2>
        <p>{{ isRegister ? '创建账号开始职业规划' : '登录后解锁更多功能' }}</p>
      </div>

      <div class="tab-switch">
        <button :class="['tab', { active: !isRegister }]" @click="isRegister = false">登录</button>
        <button :class="['tab', { active: isRegister }]" @click="isRegister = true">注册</button>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" type="text" placeholder="请输入用户名" required />
        </div>
        
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="请输入密码" required />
        </div>

        <div class="form-group" v-if="isRegister">
          <label>确认密码</label>
          <input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" required />
        </div>

        <div class="form-error" v-if="errorMsg">{{ errorMsg }}</div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '处理中...' : (isRegister ? '注册' : '登录') }}
        </button>
      </form>

      <div class="modal-footer">
        <p v-if="!isRegister">
          还没有账号？
          <a href="#" @click.prevent="isRegister = true">立即注册</a>
        </p>
        <p v-else>
          已有账号？
          <a href="#" @click.prevent="isRegister = false">立即登录</a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import { authApi } from '../api/auth'

const props = defineProps<{
  redirectPath?: string
}>()

const emit = defineEmits<{
  close: []
  success: []
}>()

const userStore = useUserStore()
const isRegister = ref(false)
const loading = ref(false)
const errorMsg = ref('')

const form = ref({
  username: '',
  password: '',
  confirmPassword: ''
})

async function handleSubmit() {
  if (!form.value.username || !form.value.password) {
    errorMsg.value = '请填写用户名和密码'
    return
  }

  if (isRegister.value) {
    if (form.value.password !== form.value.confirmPassword) {
      errorMsg.value = '两次密码输入不一致'
      return
    }
    if (form.value.password.length < 6) {
      errorMsg.value = '密码至少6位'
      return
    }
  }

  loading.value = true
  errorMsg.value = ''

  try {
    if (isRegister.value) {
      const result = await authApi.register(form.value.username, form.value.password)
      userStore.setToken(result.access_token)
      userStore.setStudent(result.student_id, result.username)
      userStore.setRole(result.role)
    } else {
      const result = await authApi.login(form.value.username, form.value.password)
      userStore.setToken(result.access_token)
      userStore.setStudent(result.student_id, result.username)
      userStore.setRole(result.role)
    }
    emit('success')
  } catch (e: any) {
    errorMsg.value = e.message || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.login-modal {
  background: white;
  border-radius: 20px;
  padding: 32px;
  width: 400px;
  max-width: 90vw;
  position: relative;
  animation: modal-in 0.3s ease;
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 20px;
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #333;
}

.modal-header {
  text-align: center;
  margin-bottom: 24px;
}

.modal-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.modal-header p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.tab-switch {
  display: flex;
  background: #f5f5f5;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 24px;
}

.tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.tab.active {
  background: white;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input:focus {
  border-color: #667eea;
}

.form-error {
  color: #f5222d;
  font-size: 13px;
  margin-bottom: 16px;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #666;
}

.modal-footer a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.modal-footer a:hover {
  text-decoration: underline;
}
</style>
