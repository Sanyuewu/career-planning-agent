import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type AuthResult } from '@/api/auth'
import { clearAuth } from '@/lib/http'

// 身份与会话：谁在用（studentId / 角色 / token）。
// 注：dev(AUTH_ENFORCED=false) 下可只有 studentId 无 token（上传简历即得 id）。
export const useSession = defineStore('session', () => {
  const studentId = ref<string | null>(localStorage.getItem('student_id'))
  const name = ref(localStorage.getItem('student_name') || '')
  const role = ref(localStorage.getItem('user_role') || '')
  const token = ref<string | null>(localStorage.getItem('access_token'))

  const isLoggedIn = computed(() => !!token.value || !!studentId.value)
  const isPlatform = computed(() => role.value === 'platform_admin')
  const isStaff = computed(() => role.value === 'teacher' || role.value === 'admin')
  const isStudent = computed(() => !isPlatform.value && !isStaff.value)
  const displayName = computed(() => name.value || '同学')

  function apply(r: AuthResult) {
    token.value = r.access_token
    role.value = r.role
    if (r.student_id) studentId.value = r.student_id
    name.value = r.username || name.value
    localStorage.setItem('access_token', r.access_token)
    if (r.refresh_token) localStorage.setItem('refresh_token', r.refresh_token)
    localStorage.setItem('user_role', r.role)
    if (r.student_id) localStorage.setItem('student_id', r.student_id)
    localStorage.setItem('student_name', name.value)
  }

  async function login(u: string, p: string) { apply(await authApi.login(u, p)) }
  async function register(u: string, p: string) { apply(await authApi.register(u, p)) }

  function setStudentId(id: string, nm?: string) {
    studentId.value = id
    localStorage.setItem('student_id', id)
    if (nm) { name.value = nm; localStorage.setItem('student_name', nm) }
  }

  function logout() {
    studentId.value = null; name.value = ''; role.value = ''; token.value = null
    clearAuth()
  }

  return { studentId, name, role, token, isLoggedIn, isStudent, isStaff, isPlatform, displayName,
    login, register, setStudentId, logout }
})
