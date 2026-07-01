import { http } from '@/lib/http'

export interface CurvePoint { date: string; value: number | null; job_name?: string }

export interface ProgressTrend {
  available: boolean
  portrait_versions?: number
  competitiveness_curve?: CurvePoint[]
  completeness_curve?: CurvePoint[]
  match_curve?: CurvePoint[]
  competitiveness_delta?: number | null
  skill_growth?: string[]
}

export interface GrowthAttribution {
  available: boolean
  competitiveness_delta?: number | null
  new_skills?: string[]
  drivers?: string[]
}

export interface MatchProgress {
  available: boolean
  job_name?: string
  prev_total?: number
  curr_total?: number
  total_delta?: number
  resolved_missing?: string[]
  still_missing?: string[]
}

export interface ActionCompletion {
  available: boolean
  plan_id?: string
  job_name?: string
  total?: number
  done?: number
  in_progress?: number
  overdue?: number
  completion_pct?: number
}

export interface ProgressResponse {
  student_id: string
  trend: ProgressTrend
  growth: GrowthAttribution
  match_progress: MatchProgress
  actions: ActionCompletion
}

export interface ActionItem {
  id: string
  title: string
  description?: string
  timeline?: string
  status?: string
  due_date?: string
  completed_at?: string
  milestones?: string[]
}

export interface ActionPlanResponse {
  has_plan: boolean
  student_id: string
  plan?: { id: string; job_name?: string; status: string; items: ActionItem[] }
  completion?: ActionCompletion
}

export const progressApi = {
  get: (sid: string) => http.get<ProgressResponse>(`/progress/${sid}`),
  actionPlan: (sid: string) => http.get<ActionPlanResponse>(`/action/${sid}`),
  completeItem: (sid: string, itemId: string) =>
    http.post<{ success: boolean; completion: ActionCompletion }>(`/action/${sid}/item/${itemId}/complete`),
}
