/**
 * 错误处理工具函数
 * 统一错误消息提取和处理
 */

import { Message } from '@arco-design/web-vue'
import { MESSAGES } from '../constants'

export interface ApiError {
  response?: {
    status?: number
    data?: {
      detail?: string
      message?: string
      errors?: Array<{ field: string; message: string }>
    }
  }
  message?: string
  code?: string
}

const STATUS_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: '请先登录',
  403: '权限不足',
  404: '资源不存在',
  405: '请求方法不允许',
  408: '请求超时',
  409: '资源冲突',
  413: '文件大小超出限制',
  422: '数据验证失败',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂时不可用',
  504: '网关超时',
}

export function getErrorMessage(error: unknown, fallback: string = MESSAGES.ERROR.NETWORK): string {
  if (!error) return fallback
  
  if (typeof error === 'string') return error
  
  const apiError = error as ApiError
  
  if (apiError.response?.data?.detail) {
    return apiError.response.data.detail
  }
  
  if (apiError.response?.data?.message) {
    return apiError.response.data.message
  }
  
  if (apiError.response?.status) {
    const status = apiError.response.status
    if (STATUS_MESSAGES[status]) {
      return STATUS_MESSAGES[status]
    }
  }
  
  if (apiError.message) {
    if (apiError.message.includes('timeout')) {
      return MESSAGES.ERROR.TIMEOUT
    }
    if (apiError.message.includes('Network Error') || apiError.message.includes('network')) {
      return MESSAGES.ERROR.NETWORK
    }
    return apiError.message
  }
  
  return fallback
}

export function getValidationErrors(error: unknown): Array<{ field: string; message: string }> {
  const apiError = error as ApiError
  return apiError?.response?.data?.errors || []
}

export function isNetworkError(error: unknown): boolean {
  const apiError = error as ApiError
  return (
    apiError?.message?.includes('Network Error') ||
    apiError?.message?.includes('network') ||
    !apiError?.response
  )
}

export function isTimeoutError(error: unknown): boolean {
  const apiError = error as ApiError
  return (
    apiError?.message?.includes('timeout') ||
    apiError?.response?.status === 408
  )
}

export function isAuthError(error: unknown): boolean {
  const apiError = error as ApiError
  return apiError?.response?.status === 401
}

export function isForbiddenError(error: unknown): boolean {
  const apiError = error as ApiError
  return apiError?.response?.status === 403
}

export function isNotFoundError(error: unknown): boolean {
  const apiError = error as ApiError
  return apiError?.response?.status === 404
}

export function isValidationError(error: unknown): boolean {
  const apiError = error as ApiError
  return apiError?.response?.status === 422 || apiError?.response?.status === 400
}

export function showError(error: unknown, fallback?: string): void {
  const message = getErrorMessage(error, fallback)
  Message.error(message)
}

export function showWarning(message: string): void {
  Message.warning(message)
}

export function showSuccess(message: string): void {
  Message.success(message)
}

export function showInfo(message: string): void {
  Message.info(message)
}

export function handleApiError(error: unknown, options?: {
  fallback?: string
  onAuthError?: () => void
  onNetworkError?: () => void
  onValidationError?: (errors: Array<{ field: string; message: string }>) => void
}): void {
  const { fallback, onAuthError, onNetworkError, onValidationError } = options || {}
  
  if (isAuthError(error)) {
    onAuthError?.()
    showError(MESSAGES.ERROR.UNAUTHORIZED)
    return
  }
  
  if (isNetworkError(error)) {
    onNetworkError?.()
    showError(MESSAGES.ERROR.NETWORK)
    return
  }
  
  if (isValidationError(error) && onValidationError) {
    const errors = getValidationErrors(error)
    onValidationError(errors)
    return
  }
  
  showError(error, fallback)
}

export class AppError extends Error {
  code: string
  status: number
  
  constructor(message: string, code: string = 'UNKNOWN', status: number = 500) {
    super(message)
    this.code = code
    this.status = status
    this.name = 'AppError'
  }
}

export function createError(message: string, code?: string, status?: number): AppError {
  return new AppError(message, code, status)
}
