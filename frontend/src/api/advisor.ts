import { http } from '@/lib/http'
import { streamSSE, type SSEHandle } from '@/lib/sse'

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ChatSession {
  session_id: string
  student_id?: string
  job_name?: string
  messages: ChatMessage[]
  title?: string
  created_at?: string
  updated_at?: string
}

export interface SessionListItem { id: string; title: string; updatedAt: string; messageCount: number }

export const advisorApi = {
  createSession: (sid?: string, jobName?: string) =>
    http.post<ChatSession>('/chat/session', undefined, { student_id: sid, match_job_name: jobName }),
  getSession: (id: string) => http.get<ChatSession>(`/chat/session/${id}`),
  listSessions: (sid?: string) => http.get<SessionListItem[]>('/chat/sessions', { student_id: sid }),
  deleteSession: (id: string) => http.del(`/chat/session/${id}`),

  /** 自由问答（真流式）：事件 {token} 增量 / {full_response} 收尾 / {error} */
  streamChat: (
    sessionId: string, text: string,
    onEvent: (ev: any) => void, opts?: { onError?: (e: string) => void; onDone?: () => void },
  ): SSEHandle => streamSSE('/chat/stream', { session_id: sessionId, content: text }, onEvent, opts || {}),

  /** 结构化规划（FSM 编排）：事件 {type: state|token|tool_call|tool_result|transition|blocked|done|error} */
  runAgent: (
    sid: string, goal: string,
    onEvent: (ev: any) => void, opts?: { onError?: (e: string) => void; onDone?: () => void },
  ): SSEHandle => streamSSE('/agent/run', { student_id: sid, goal }, onEvent, opts || {}),
}
