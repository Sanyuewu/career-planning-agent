import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { Message } from '@arco-design/web-vue'

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token))
  refreshSubscribers = []
}

function onRefreshFailed() {
  refreshSubscribers = []
  clearAuthAndRedirect()
}

function clearAuthAndRedirect() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('student_id')
  localStorage.removeItem('student_name')
  localStorage.removeItem('user_role')
  localStorage.removeItem('userProfile')
  localStorage.removeItem('matchResult')
  
  import('../stores/useUserStore').then(({ useUserStore }) => {
    try { useUserStore().logout() } catch {}
  })
  
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null
  
  try {
    const response = await axios.post('/api/auth/refresh', {
      refresh_token: refreshToken
    }, {
      headers: { 'Content-Type': 'application/json' },
      skipAuthRefresh: true
    } as any)
    
    const { access_token, refresh_token } = response.data
    localStorage.setItem('access_token', access_token)
    if (refresh_token) {
      localStorage.setItem('refresh_token', refresh_token)
    }
    return access_token
  } catch {
    return null
  }
}

http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    config.headers['X-Request-ID'] = Math.random().toString(36).slice(2, 14)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

const ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数有误，请检查输入',
  401: '登录已过期，请重新登录',
  403: '无权访问该内容',
  404: '未找到相关数据',
  422: '数据格式不正确',
  429: '请求过于频繁，请稍后再试',
  500: '服务器开小差了，请稍后重试',
  502: '服务不可用，请稍后重试',
  503: '服务维护中，请稍后再试',
}

http.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const status = error.response?.status
    const serverMsg = error.response?.data?.detail || error.response?.data?.message
    
    if (status === 401 && originalRequest && !originalRequest._retry) {
      if ((originalRequest as any).skipAuthRefresh) {
        return Promise.reject(error)
      }
      
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(http.request(originalRequest))
          })
        })
      }
      
      isRefreshing = true
      originalRequest._retry = true
      
      try {
        const newToken = await refreshAccessToken()
        if (newToken) {
          onRefreshed(newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return http.request(originalRequest)
        }
      } catch (refreshError) {
        onRefreshFailed()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
      
      clearAuthAndRedirect()
      return Promise.reject(error)
    }
    
    if (status === 401) {
      clearAuthAndRedirect()
      return Promise.reject(error)
    }
    
    const displayMsg = serverMsg || ERROR_MESSAGES[status] || error.message || '请求失败'
    Message.error(displayMsg)
    
    return Promise.reject(new Error(displayMsg))
  }
)

export const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return http.get(url, config)
  },
  
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return http.post(url, data, config)
  },
  
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return http.put(url, data, config)
  },
  
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return http.patch(url, data, config)
  },
  
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return http.delete(url, config)
  },
  
  upload<T = any>(url: string, file: File, onProgress?: (percent: number) => void): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)
    
    return http.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    })
  },
}

export default http
