import { http } from '@/lib/http'

export interface MatchDimension { score: number; detail?: string }

export interface MatchResult {
  job_title?: string
  overall_score: number
  confidence?: number
  eligible?: boolean
  veto_reason?: string
  dimensions?: {
    basic_requirements?: MatchDimension
    professional_skills?: MatchDimension
    professional_qualities?: MatchDimension
    development_potential?: MatchDimension
  }
  matched_skills?: string[]
  gap_skills?: Array<{ skill: string }>
  weight_used?: Record<string, number>
  summary?: string
}

export interface Recommendation {
  job_title: string
  score: number
  intent_fit?: number
  matched_skills?: string[]
  summary?: string
  intent_note?: string
}

function normalizeJobs(res: any): string[] {
  if (Array.isArray(res)) return res
  const jobs = res?.jobs || []
  return jobs.map((j: any) => j.title || j.job_name || j)
}

export const matchApi = {
  compute: (sid: string, jobName: string, preset = 'default') =>
    http.post<MatchResult>('/match/compute', { student_id: sid, job_name: jobName, weight_preset: preset }),
  batch: (sid: string, jobNames: string[]) =>
    http.post<MatchResult[]>('/match/batch', { student_id: sid, job_names: jobNames }),
  jobs: () => http.get('/match/jobs').then(normalizeJobs),
  history: (sid: string) => http.get<MatchResult[]>(`/match/history/${sid}`),
  recommend: (sid: string, topK = 6) =>
    http.get<{ recommendations: Recommendation[] }>(`/match/recommend/${sid}`, { top_k: topK }, true),
}
