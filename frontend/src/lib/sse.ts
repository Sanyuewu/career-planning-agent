// SSE 流式消费（fetch + ReadableStream）。供 AI 顾问的自由问答(/chat/stream)
// 与结构化规划(/agent/run)共用。逐行解析 `data: <json>`，回调每个事件对象。
import { getToken } from './http'

export interface SSEHandle { cancel: () => void }

export function streamSSE(
  path: string,
  body: any,
  onEvent: (ev: any) => void,
  opts: { onError?: (e: string) => void; onDone?: () => void } = {},
): SSEHandle {
  const ctrl = new AbortController()

  ;(async () => {
    try {
      const tk = getToken()
      const res = await fetch(`/api${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(tk ? { Authorization: `Bearer ${tk}` } : {}),
        },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      })
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const raw = line.slice(5).trim()
          if (!raw || raw === '[DONE]') continue
          try { onEvent(JSON.parse(raw)) } catch { /* 半包，忽略 */ }
        }
      }
      opts.onDone?.()
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      opts.onError?.(e?.message || '流式连接失败')
    }
  })()

  return { cancel: () => ctrl.abort() }
}
