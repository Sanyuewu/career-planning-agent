import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface StudentInfo {
  completeness?: number
  competitiveness?: number
  competitivenessLevel?: string
}

export interface UserProfile {
  studentId: string
  name: string
  school: string
  major?: string
  skills: string[]
  education: any[]
  internships: any[]
  projects: any[]
  completeness: number
  competitiveness: number
  competitivenessLevel: string
}

export const useUserStore = defineStore('user', () => {
  const studentId = ref<string | null>(localStorage.getItem('student_id'))
  const studentName = ref<string>(localStorage.getItem('student_name') || '')
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const role = ref<string>(localStorage.getItem('user_role') || '')
  const studentInfo = ref<StudentInfo | null>(null)
  const profile = ref<UserProfile | null>(null)

  const isLoggedIn = computed(() => !!studentId.value || !!accessToken.value)
  const isAdmin = computed(() => role.value === 'admin')
  const isCompany = computed(() => role.value === 'company')
  const isStudent = computed(() => role.value === 'student' || !role.value)
  const userName = computed(() => studentName.value || profile.value?.name || '用户')

  function setRole(r: string) {
    role.value = r
    localStorage.setItem('user_role', r)
  }
  
  async function setStudent(id: string, name: string) {
    studentId.value = id
    studentName.value = name
    localStorage.setItem('student_id', id)
    localStorage.setItem('student_name', name)
  }
  
  function setStudentInfo(info: StudentInfo) {
    studentInfo.value = info
  }
  
  function setToken(token: string, refresh?: string) {
    accessToken.value = token
    localStorage.setItem('access_token', token)
    if (refresh) {
      refreshToken.value = refresh
      localStorage.setItem('refresh_token', refresh)
    }
  }
  
  function setProfile(data: Partial<UserProfile> & { studentId: string }) {
    profile.value = {
      studentId: data.studentId,
      name: data.name || '',
      school: data.school || '',
      major: data.major,
      skills: data.skills || [],
      education: data.education || [],
      internships: data.internships || [],
      projects: data.projects || [],
      completeness: data.completeness || 0,
      competitiveness: data.competitiveness || 0,
      competitivenessLevel: data.competitivenessLevel || '一般',
    }
    
    studentId.value = data.studentId
    studentName.value = data.name || ''
    studentInfo.value = {
      completeness: data.completeness,
      competitiveness: data.competitiveness,
      competitivenessLevel: data.competitivenessLevel,
    }
    
    localStorage.setItem('student_id', data.studentId)
    localStorage.setItem('student_name', data.name || '')
    localStorage.setItem('userProfile', JSON.stringify(profile.value))
  }
  
  function loadFromStorage() {
    const savedProfile = localStorage.getItem('userProfile')
    const savedStudentId = localStorage.getItem('student_id')
    const savedStudentName = localStorage.getItem('student_name')
    
    if (savedStudentId) {
      studentId.value = savedStudentId
    }
    
    if (savedStudentName) {
      studentName.value = savedStudentName
    }
    
    if (savedProfile) {
      try {
        const parsed: UserProfile = JSON.parse(savedProfile)
        profile.value = parsed
        studentInfo.value = {
          completeness: parsed.completeness,
          competitiveness: parsed.competitiveness,
          competitivenessLevel: parsed.competitivenessLevel,
        }
      } catch (e) {
        console.error('Failed to parse saved profile:', e)
      }
    }
    
  }
  
  async function logout() {
    studentId.value = null
    studentName.value = ''
    accessToken.value = null
    refreshToken.value = null
    role.value = ''
    studentInfo.value = null
    profile.value = null
    localStorage.removeItem('student_id')
    localStorage.removeItem('student_name')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('userProfile')
    
    const [{ usePortraitStore }, { useMatchStore }, { useReportStore }] = await Promise.all([
      import('./usePortraitStore'),
      import('./useMatchStore'),
      import('./useReportStore')
    ])
    usePortraitStore().clearAllPortraitData()
    useMatchStore().clearAllMatchData()
    useReportStore().clearAllReportData()
  }
  
  function clearAll() {
    logout()
  }

  /** 检测 JWT Token 是否已过期（无需请求后端） */
  function isTokenExpired(): boolean {
    const token = localStorage.getItem('access_token')
    if (!token) return true
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()
    } catch {
      return true
    }
  }

  /** 检测 JWT Token 是否即将过期（5分钟内） */
  function isTokenExpiringSoon(): boolean {
    const token = localStorage.getItem('access_token')
    if (!token) return true
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      if (typeof payload.exp !== 'number') return true
      const expiresAt = payload.exp * 1000
      const now = Date.now()
      const fiveMinutes = 5 * 60 * 1000
      return expiresAt - now < fiveMinutes
    } catch {
      return true
    }
  }

  /** 尝试刷新Token */
  async function tryRefreshToken(): Promise<boolean> {
    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) return false
    
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      })
      
      if (!response.ok) return false
      
      const data = await response.json()
      localStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      accessToken.value = data.access_token
      if (data.refresh_token) {
        refreshToken.value = data.refresh_token
      }
      return true
    } catch {
      return false
    }
  }

  /** 静默验证localStorage中的student_id是否在后端实际存在，不存在则清除 */
  async function validateStudent(): Promise<void> {
    const id = studentId.value
    if (!id) return
    try {
      const resp = await fetch(`/api/portrait/${id}`)
      if (resp.status === 404) {
        console.warn('[UserStore] student_id不存在于后端，清除本地缓存:', id)
        logout()
      }
    } catch {
      // 网络错误时不清除，保留本地状态
    }
  }

  loadFromStorage()
  
  return {
    studentId,
    studentName,
    accessToken,
    refreshToken,
    role,
    studentInfo,
    profile,
    isLoggedIn,
    isAdmin,
    isCompany,
    isStudent,
    userName,
    setStudent,
    setStudentInfo,
    setToken,
    setRole,
    setProfile,
    loadFromStorage,
    isTokenExpired,
    isTokenExpiringSoon,
    tryRefreshToken,
    validateStudent,
    logout,
    clearAll,
  }
})
