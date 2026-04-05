/**
 * localStorage 工具函数
 * 为 Pinia stores 提供统一的缓存管理，避免重复实现
 */

/**
 * 清除 localStorage 中属于其他用户的 key
 * @param prefixes  key 前缀列表（每个 key 格式为 prefix + studentId）
 * @param currentId 当前登录用户 ID（其对应的 key 保留）
 */
export function clearOtherUsersKeys(prefixes: string[], currentId: string): void {
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (!key) continue
    for (const prefix of prefixes) {
      if (key.startsWith(prefix) && key.substring(prefix.length) !== currentId) {
        keysToRemove.push(key)
        break
      }
    }
  }
  keysToRemove.forEach(key => localStorage.removeItem(key))
}

/**
 * 清除 localStorage 中所有匹配前缀的 key 及额外指定的 key
 */
export function clearAllKeys(prefixes: string[], extraKeys?: string[]): void {
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (!key) continue
    if (prefixes.some(p => key.startsWith(p)) || extraKeys?.includes(key)) {
      keysToRemove.push(key)
    }
  }
  keysToRemove.forEach(key => localStorage.removeItem(key))
}

/**
 * 检查时间戳 key 是否已超过指定时长（过期）
 */
export function isExpired(tsKey: string, staleMs: number): boolean {
  const ts = localStorage.getItem(tsKey)
  if (!ts) return true
  return Date.now() - parseInt(ts) > staleMs
}
