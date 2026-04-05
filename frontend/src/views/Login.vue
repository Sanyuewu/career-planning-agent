<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">🎓</div>
        <h1>职业规划智能体</h1>
        <p>AI驱动的大学生职业发展平台</p>
      </div>

      <div class="tab-bar">
        <button
          class="tab-btn"
          :class="{ active: mode === 'login' }"
          @click="mode = 'login'"
        >登录</button>
        <button
          class="tab-btn"
          :class="{ active: mode === 'register' }"
          @click="mode = 'register'"
        >注册</button>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <div class="form-field">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            placeholder="请输入用户名"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-field">
          <label>密码</label>
          <input
            v-model="password"
            type="password"
            placeholder="请输入密码（至少6位）"
            autocomplete="current-password"
            required
          />
        </div>

        <!-- 注册时的角色选择 -->
        <div v-if="mode === 'register'" class="form-field">
          <label>账号类型</label>
          <div class="role-selector">
            <button
              type="button"
              class="role-btn"
              :class="{ active: registerRole === 'student' }"
              @click="registerRole = 'student'"
            >
              <span class="role-icon">🎓</span>
              <span class="role-label">学生</span>
              <span class="role-desc">上传简历・匹配岗位</span>
            </button>
            <button
              type="button"
              class="role-btn"
              :class="{ active: registerRole === 'company' }"
              @click="registerRole = 'company'"
            >
              <span class="role-icon">🏢</span>
              <span class="role-label">企业</span>
              <span class="role-desc">发布需求・寻找人才</span>
            </button>
          </div>
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
        </button>
      </form>

      <!-- 游客模式暂时隐藏
      <div class="divider">或</div>
      <button class="guest-btn" @click="continueAsGuest">
        游客模式继续（不保存登录状态）
      </button>
      -->

      <p class="security-note">
        🔒 您的数据通过 JWT 加密传输，账号信息安全存储
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/useUserStore'
import { request } from '../api/http'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const registerRole = ref<'student' | 'company'>('student')
const loading = ref(false)
const error = ref('')

async function submit() {
  if (!username.value || !password.value) return
  error.value = ''
  loading.value = true

  try {
    const endpoint = mode.value === 'login' ? '/auth/login' : '/auth/register'
    const body: any = { username: username.value, password: password.value }
    if (mode.value === 'register') body.role = registerRole.value

    const result = await request.post<{ access_token: string; refresh_token: string; student_id: string; username: string; role: string }>(
      endpoint,
      body
    )

    userStore.setToken(result.access_token, result.refresh_token || '')
    userStore.setRole(result.role || 'student')
    if (result.student_id) {
      userStore.setStudent(result.student_id, result.username)
      
      const [{ usePortraitStore }, { useMatchStore }, { useReportStore }] = await Promise.all([
        import('../stores/usePortraitStore'),
        import('../stores/useMatchStore'),
        import('../stores/useReportStore')
      ])
      usePortraitStore().clearOtherUsersData(result.student_id)
      useMatchStore().clearAllMatchData()
      useReportStore().clearOtherUsersData(result.student_id)
    }

    const redirect = route.query.redirect as string
    if (redirect) {
      router.push(redirect)
    } else if (result.role === 'company') {
      router.push('/company')
    } else if (result.role === 'admin') {
      router.push('/admin')
    } else {
      router.push('/home')
    }
  } catch (e: any) {
    error.value = e?.message || (mode.value === 'login' ? '用户名或密码错误' : '注册失败，请重试')
  } finally {
    loading.value = false
  }
}

// function continueAsGuest() {
//   Message.info('游客模式功能受限：无法保存匹配历史，建议登录后使用完整功能')
//   const redirect = (route.query.redirect as string) || '/upload'
//   router.push(redirect)
// }
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  background: #fff;
  border-radius: 20px;
  padding: 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-logo {
  font-size: 48px;
  margin-bottom: 12px;
}

.login-header h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px;
}

.login-header p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.tab-bar {
  display: flex;
  border-radius: 10px;
  background: #f5f5f5;
  padding: 4px;
  margin-bottom: 24px;
}

.tab-btn {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: #fff;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.form-field input {
  padding: 12px 14px;
  border: 1.5px solid #e0e0e0;
  border-radius: 10px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}

.form-field input:focus {
  border-color: #667eea;
}

.error-msg {
  background: #fff5f5;
  color: #e53e3e;
  border: 1px solid #fed7d7;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
}

.submit-btn {
  padding: 14px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-top: 4px;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.divider {
  text-align: center;
  color: #999;
  font-size: 13px;
  margin: 16px 0;
  position: relative;
}

.divider::before,
.divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 40%;
  height: 1px;
  background: #eee;
}

.divider::before { left: 0; }
.divider::after { right: 0; }

.guest-btn {
  width: 100%;
  padding: 12px;
  background: #f8fafc;
  color: #555;
  border: 1.5px solid #e0e0e0;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.guest-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.security-note {
  text-align: center;
  font-size: 12px;
  color: #999;
  margin: 16px 0 0;
}

.role-selector {
  display: flex;
  gap: 12px;
}

.role-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 10px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: #fafafa;
  cursor: pointer;
  transition: all 0.2s;
}

.role-btn.active {
  border-color: #667eea;
  background: #f0f4ff;
}

.role-icon {
  font-size: 24px;
}

.role-label {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.role-desc {
  font-size: 11px;
  color: #888;
}

.role-btn.active .role-label {
  color: #667eea;
}

@media (max-width: 768px) {
  .login-page {
    padding: 16px;
  }

  .login-card {
    padding: 28px 20px;
    border-radius: 16px;
  }

  .login-logo {
    font-size: 40px;
  }

  .login-header h1 {
    font-size: 20px;
  }

  .login-header p {
    font-size: 13px;
  }

  .tab-bar {
    margin-bottom: 20px;
  }

  .tab-btn {
    padding: 8px;
    font-size: 14px;
  }

  .form-field input {
    padding: 10px 12px;
    font-size: 14px;
  }

  .submit-btn {
    padding: 12px;
    font-size: 15px;
  }

  .guest-btn {
    padding: 10px;
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 24px 16px;
  }

  .login-logo {
    font-size: 36px;
    margin-bottom: 8px;
  }

  .login-header h1 {
    font-size: 18px;
  }

  .login-header p {
    font-size: 12px;
  }

  .role-selector {
    flex-direction: column;
    gap: 10px;
  }

  .role-btn {
    flex-direction: row;
    padding: 12px 14px;
    gap: 12px;
    justify-content: flex-start;
  }

  .role-icon {
    font-size: 28px;
  }

  .role-label {
    font-size: 14px;
  }

  .role-desc {
    font-size: 11px;
  }

  .form-field label {
    font-size: 13px;
  }

  .form-field input {
    padding: 10px 12px;
    font-size: 14px;
  }

  .submit-btn {
    padding: 12px;
    font-size: 14px;
  }

  .divider {
    margin: 14px 0;
    font-size: 12px;
  }

  .security-note {
    font-size: 11px;
  }
}
</style>
