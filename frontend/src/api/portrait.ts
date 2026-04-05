import { request } from './http'

import type { Education, Experience, Project } from '../types/index'

export interface PortraitResponse {
  student_id: string
  basic_info: {
    name?: string
    school?: string
    major?: string
    grade?: string
  }
  education: Education[]
  skills: string[]
  internships: Experience[]
  projects: Project[]
  certs: string[]
  awards: string[]
  career_intent?: string
  inferred_soft_skills: Record<string, { score?: number; evidence?: string }>
  completeness: number
  competitiveness: number
  competitiveness_level: string
  highlights: string[]
  weaknesses: string[]
  transfer_opportunities?: Array<{
    target: string
    match_level?: string
    overlap_pct?: number
    advantage?: string
    need_learn?: string
  }>
  interests?: string[]
  ability_profile?: Record<string, number>
  personality_traits?: string[]
  preferred_cities?: string[]
  culture_preference?: string[]
}

export const portraitApi = {
  get(studentId: string): Promise<PortraitResponse> {
    return request.get(`/portrait/${studentId}`)
  },
  
  update(studentId: string, data: {
    basic_info?: {
      name?: string
      school?: string
      major?: string
      grade?: string
      phone?: string
      email?: string
    }
    skills?: string[]
    certs?: string[]
    awards?: string[]
    education?: any[]
    internships?: any[]
    projects?: any[]
    career_intent?: string
    interests?: string[]
  }): Promise<PortraitResponse> {
    return request.put(`/portrait/${studentId}`, data)
  },

  getScoreDetail(studentId: string): Promise<any> {
    return request.get(`/portrait/${studentId}/score_detail`)
  },
}
