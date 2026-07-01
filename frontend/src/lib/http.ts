// 轻量 HTTP 客户端（从零，fetch 实现）。统一鉴权头、401 单飞刷新、错误 Toast、JSON 解析。
// 后端契约不变：baseURL=/api（Vite 代理 → :8082）。
import { Message } from '@arco-design/web-vue'

const BASE = '/api'

const ERR: Record<number, string> = {
  400: '请求参数有误', 401: '登录已过期，请重新登录', 403: '无权访问',
  404: '未找到相关数据', 422: '数据格式不正确', 429: '请求过于频繁，请稍后再试',
  500: '服务器开小差了', 502: '服务不可用', 503: '服务维护中',
}

export function getToken() { return localStorage.getItem('access_token') }

export function clearAuth() {
  ;['access_token', 'refresh_token', 'student_id', 'student_name', 'user_role'].forEach(k =>
    localStorage.removeItem(k))
}

let refreshing: Promise<string | null> | null = null
async function refreshToken(): Promise<string | null> {
  const rt = localStorage.getItem('refresh_token')
  if (!rt) return null
  try {
    const r = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    if (!r.ok) return null
    const d = await r.json()
    localStorage.setItem('access_token', d.access_token)
    if (d.refresh_token) localStorage.setItem('refresh_token', d.refresh_token)
    return d.access_token
  } catch { return null }
}

export interface ReqOpts {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: any
  query?: Record<string, any>
  silent?: boolean            // 不弹错误 Toast（调用方自行处理）
}

function buildUrl(path: string, query?: Record<string, any>): string {
  let url = BASE + path
  if (query) {
    const qs = new URLSearchParams()
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.append(k, String(v))
    })
    const s = qs.toString()
    if (s) url += `?${s}`
  }
  return url
}

async function request<T = any>(path: string, opts: ReqOpts = {}): Promise<T> {
  const { method = 'GET', body, query, silent } = opts
  const url = buildUrl(path, query)

  const fire = (tk: string | null) => {
    const headers: Record<string, string> = {}
    let payload: BodyInit | undefined
    if (body instanceof FormData) payload = body
    else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
    if (tk) headers['Authorization'] = `Bearer ${tk}`
    return fetch(url, { method, headers, body: payload })
  }

  let res: Response
  try {
    res = await fire(getToken())
  } catch (e: any) {
    if (!silent) Message.error('网络异常，请检查连接')
    throw new Error(e?.message || 'network error')
  }

  if (res.status === 401 && localStorage.getItem('refresh_token')) {
    if (!refreshing) refreshing = refreshToken().finally(() => { refreshing = null })
    const nt = await refreshing
    if (nt) res = await fire(nt)
    else {
      clearAuth()
      if (location.pathname !== '/login') location.href = '/login'
      throw new Error('登录已过期')
    }
  }

  if (!res.ok) {
    let detail = ''
    try { const e = await res.json(); detail = e.detail || e.message || '' } catch { /* noop */ }
    const msg = detail || ERR[res.status] || `请求失败 (${res.status})`
    if (!silent) Message.error(msg)
    throw new Error(msg)
  }

  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json() as Promise<T>
  return res as unknown as T   // 文件流等非 JSON 由调用方处理
}

export const http = {
  get:  <T = any>(path: string, query?: Record<string, any>, silent?: boolean) =>
          request<T>(path, { method: 'GET', query, silent }),
  post: <T = any>(path: string, body?: any, query?: Record<string, any>, silent?: boolean) =>
          request<T>(path, { method: 'POST', body, query, silent }),
  put:  <T = any>(path: string, body?: any) => request<T>(path, { method: 'PUT', body }),
  del:  <T = any>(path: string) => request<T>(path, { method: 'DELETE' }),
  /** 文件上传（multipart），字段名 file，可报告进度 */
  upload: <T = any>(path: string, file: File): Promise<T> => {
    const fd = new FormData(); fd.append('file', file)
    return request<T>(path, { method: 'POST', body: fd })
  },
  /** 取原始 Response（用于 PDF/Word 文件流下载） */
  raw: (path: string): Promise<Response> => {
    const headers: Record<string, string> = {}
    const tk = getToken(); if (tk) headers['Authorization'] = `Bearer ${tk}`
    return fetch(BASE + path, { headers })
  },
}
