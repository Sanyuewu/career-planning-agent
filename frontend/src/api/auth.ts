import { http } from '@/lib/http'

export interface AuthResult {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in?: number
  student_id: string
  username: string
  role: string
  tenant_id?: string
}

export const authApi = {
  login: (username: string, password: string) =>
    http.post<AuthResult>('/auth/login', { username, password }),
  register: (username: string, password: string, studentId?: string) =>
    http.post<AuthResult>('/auth/register', { username, password, student_id: studentId, role: 'student' }),
  me: () => http.get('/auth/me'),
}
