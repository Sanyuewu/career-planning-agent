import { request } from './http'
import type {
  SkillMatchDetail,
  ImprovementSuggestion,
  GapAnalysis,
  ConfidenceBreakdown,
  MarketDemand,
  TransferPath,
  GapSkill,
} from '../types'

export type { SkillMatchDetail, ImprovementSuggestion, GapAnalysis, ConfidenceBreakdown, MarketDemand, TransferPath, GapSkill }

export interface MatchResult {
  job_id?: string
  job_title?: string
  overall_score: number
  confidence?: number
  dimensions?: {
    basic_requirements?: { score: number; detail?: string; evidence?: string }
    professional_skills?: { score: number; detail?: string; evidence?: string }
    professional_qualities?: { score: number; detail?: string; evidence?: string }
    development_potential?: { score: number; detail?: string; evidence?: string }
    market_demand?: MarketDemand
  }
  gap_skills?: GapSkill[]
  matched_skills?: string[]
  weight_used?: Record<string, number>
  summary?: string
  is_degraded?: boolean
  competitive_context?: string
  market_demand?: MarketDemand
  skill_match_details?: SkillMatchDetail[]
  gap_analysis?: GapAnalysis[]
  confidence_breakdown?: ConfidenceBreakdown
  transfer_paths?: TransferPath[]
  job_context?: {
    top_regions?: string[]
    culture_types?: string[]
    top_companies?: string[]
    education_level?: string
    majors?: string[]
    industry?: string
  }
  explanation_tree?: Array<{
    dim: string
    label: string
    score: number
    weight: number
    contribution: number
    factors: Array<{ name: string; value: string }>
  }>
}

export const matchApi = {
  compute(studentId: string, jobName: string, weightPreset: string = 'default'): Promise<MatchResult> {
    return request.post('/match/compute', {
      student_id: studentId,
      job_name: jobName,
      weight_preset: weightPreset,
    }, { timeout: 120000 })
  },
  
  batchCompute(studentId: string, jobNames: string[]): Promise<MatchResult[]> {
    return request.post('/match/batch', {
      student_id: studentId,
      job_names: jobNames,
    })
  },
  
  getJobs(): Promise<string[]> {
    return request.get('/match/jobs').then((res: any) => {
      if (Array.isArray(res)) {
        return res
      }
      const jobs = res.jobs || []
      return jobs.map((j: any) => j.title || j.job_name || j)
    })
  },
  
  getHistory(studentId: string): Promise<MatchResult[]> {
    return request.get(`/match/history/${studentId}`)
  },
  
  recommend(studentId: string, topK: number = 5): Promise<{recommendations: {job_title: string, score: number, matched_skills: string[], summary: string}[]}> {
    return request.get(`/match/recommend/${studentId}?top_k=${topK}`)
  },
}
