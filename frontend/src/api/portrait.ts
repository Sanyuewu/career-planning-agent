import { http } from '@/lib/http'

export interface SoftSkill { score?: number; evidence?: string }

export interface Portrait {
  student_id: string
  basic_info: { name?: string; school?: string; major?: string; grade?: string }
  education: any[]
  skills: string[]
  internships: any[]
  projects: any[]
  certs: string[]
  awards: string[]
  career_intent?: string
  inferred_soft_skills: Record<string, SoftSkill>
  completeness: number
  competitiveness: number
  competitiveness_level: string
  highlights: string[]
  weaknesses: string[]
  interests?: string[]
}

export interface PortraitUpdate {
  basic_info?: Record<string, any>
  skills?: string[]
  certs?: string[]
  awards?: string[]
  education?: any[]
  internships?: any[]
  projects?: any[]
  career_intent?: string
  interests?: string[]
}

export const portraitApi = {
  parse: (file: File) => http.upload<{ success: boolean; result: Portrait }>('/resume/parse', file),
  get: (sid: string) => http.get<Portrait>(`/portrait/${sid}`),
  update: (sid: string, data: PortraitUpdate) => http.put<Portrait>(`/portrait/${sid}`, data),
  scoreDetail: (sid: string) => http.get<{ overall: number; dimensions: Record<string, number>; completeness: number }>(`/portrait/${sid}/score_detail`),
}
