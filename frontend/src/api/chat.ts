import { request } from './http'

export interface ChatSession {
  session_id: string
  state: string
  messages: ChatMessage[]
  emotion_score: number
  turn_count: number
  title?: string
  created_at?: string
  updated_at?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  state?: string
  emotion?: string
  timestamp: string
}

export interface ChatMessageResponse {
  id: string
  role: string
  content: string
  state?: string
  emotion?: string
  timestamp: string
}

export interface SessionListItem {
  id: string
  title: string
  updatedAt: string
  messageCount: number
}

export const chatApi = {
  createSession(studentId?: string, matchJobName?: string): Promise<ChatSession> {
    const p = new URLSearchParams()
    if (studentId) p.set('student_id', studentId)
    if (matchJobName) p.set('match_job_name', matchJobName)
    const qs = p.toString() ? `?${p.toString()}` : ''
    return request.post(`/chat/session${qs}`)
  },
  
  getSession(sessionId: string): Promise<ChatSession> {
    return request.get(`/chat/session/${sessionId}`)
  },
  
  listSessions(studentId?: string): Promise<SessionListItem[]> {
    const params = studentId ? `?student_id=${studentId}` : ''
    return request.get(`/chat/sessions${params}`)
  },
  
  deleteSession(sessionId: string): Promise<void> {
    return request.delete(`/chat/session/${sessionId}`)
  },
  
}
