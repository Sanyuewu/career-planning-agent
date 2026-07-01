import { http } from '@/lib/http'

// ── 院校分析（teacher+admin，按角色范围）──────────────────────
export interface AnalyticsOverview {
  student_count: number
  with_portrait: number
  avg_completeness: number
  avg_competitiveness: number
  with_match: number
  intent_distribution: Array<{ intent: string; count: number }>
}
export interface SeriesPoint { month: string; avg: number; n: number }
export interface TrendsResponse {
  cohort_size: number
  competitiveness_series: SeriesPoint[]
  match_series: SeriesPoint[]
  improvement_pct: number | null
  action_completion: { avg_pct: number; items_done: number; items_total: number }
  available: boolean
}
export interface DistributionItem { label: string; count: number }
export interface SkillGapItem { skill: string; count: number }
export interface AtRiskItem {
  student_id: string; name: string; competitiveness: number; completeness: number; reasons: string[]
}
export interface RosterItem {
  student_id: string; name: string; completeness: number; competitiveness: number
  best_match: number; best_job: string; career_intent: string
}

export const analyticsApi = {
  overview: () => http.get<AnalyticsOverview>('/analytics/overview'),
  trends: () => http.get<TrendsResponse>('/analytics/trends'),
  competitivenessDistribution: () => http.get<{ distribution: DistributionItem[] }>('/analytics/competitiveness_distribution'),
  skillGaps: (topN = 12) => http.get<{ skill_gaps: SkillGapItem[] }>('/analytics/skill_gaps', { top_n: topN }),
  atRisk: () => http.get<{ at_risk: AtRiskItem[]; count: number }>('/analytics/at_risk'),
  students: () => http.get<{ students: RosterItem[]; count: number }>('/analytics/students'),
}

// ── 院校管理（admin）──────────────────────────────────────────
export interface ClassItem { id: string; name: string; student_count: number }
export interface UserItem { id: string; username: string; role: string; student_id: string | null; class_id: string | null }
export interface TeacherClassItem { teacher_id: string; teacher_name: string; class_id: string; class_name: string }
export interface TenantConfig {
  match_weights: Record<string, number> | null
  job_library: string[] | null
  report_extra_instructions: string
}

export const adminApi = {
  getTenantConfig: () => http.get<TenantConfig>('/admin/tenant/config'),
  putTenantConfig: (cfg: Partial<TenantConfig>) => http.put('/admin/tenant/config', cfg),
  listClasses: () => http.get<ClassItem[]>('/admin/classes'),
  createClass: (name: string) => http.post<{ id: string; name: string }>('/admin/classes', { name }),
  deleteClass: (id: string) => http.del(`/admin/classes/${id}`),
  listUsers: (role?: string) => http.get<UserItem[]>('/admin/users', role ? { role } : undefined),
  createUser: (username: string, password: string, role: string) =>
    http.post('/admin/users', { username, password, role }),
  roster: () => http.get<{ students: (RosterItem & { has_profile?: boolean })[] }>('/admin/roster'),
  assignStudentClass: (studentId: string, classId: string | null) =>
    http.put(`/admin/students/${studentId}/class`, { class_id: classId }),
  listTeacherClasses: () => http.get<TeacherClassItem[]>('/admin/teacher-classes'),
  assignTeacherClass: (teacherId: string, classId: string) =>
    http.post('/admin/teacher-classes', { teacher_id: teacherId, class_id: classId }),
  unassignTeacherClass: (teacherId: string, classId: string) =>
    http.del(`/admin/teacher-classes?teacher_id=${encodeURIComponent(teacherId)}&class_id=${encodeURIComponent(classId)}`),
}
