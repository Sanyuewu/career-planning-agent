import { request } from './http'

export interface AuthResult {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in?: number
  student_id: string
  username: string
  role: string
}

export const authApi = {
  async register(username: string, password: string, studentId?: string): Promise<AuthResult> {
    return request.post<AuthResult>('/auth/register', {
      username,
      password,
      student_id: studentId,
      role: 'student'
    })
  },

  async login(username: string, password: string): Promise<AuthResult> {
    return request.post<AuthResult>('/auth/login', {
      username,
      password
    })
  },

  async refreshToken(refreshToken: string): Promise<AuthResult> {
    return request.post<AuthResult>('/auth/refresh', {
      refresh_token: refreshToken
    })
  },

  async getMe(): Promise<{ username: string; student_id: string; role: string }> {
    return request.get('/auth/me')
  }
}
