import { request } from './http'

export interface UserStatsResponse {
  portrait_completeness: number
  match_count: number
  report_count: number
  chat_session_count: number
  last_active_at: string
  achievements: string[]
  activity_trend: Array<{
    date: string
    matches: number
    reports: number
  }>
  skill_progress: Record<string, {
    current: number
    target: number
  }>
}

export interface SkillScoreItem {
  name: string
  score: number
  level: string
  category: string
  certified: boolean
  evidence: string[]
  learning_progress?: number
}

export interface SoftSkillItem {
  name: string
  score: number
  evidence: string
  improvement_suggestions: string[]
}

export interface SkillScoresResponse {
  skills: SkillScoreItem[]
  soft_skills: SoftSkillItem[]
}

export interface CompetitivenessHistoryItem {
  date: string
  score: number
  level: string
}

export interface PeerComparison {
  avg: number
  percentile: number
}

export interface PeerComparisonData {
  same_major: PeerComparison
  same_grade: PeerComparison
}

export interface CompetitivenessHistoryResponse {
  history: CompetitivenessHistoryItem[]
  peer_comparison: PeerComparisonData
}

export interface IndustryTrend {
  industry: string
  trend: string
  job_count: number
  avg_salary: string
  growth: string
  hot_skills: string[]
  outlook: string
}

export interface IndustryTrendsResponse {
  trends: IndustryTrend[]
}

export interface AchievementItem {
  id: string
  name: string
  icon: string
  description: string
  unlocked_at: string | null
  progress: number
}

export interface AchievementsResponse {
  achievements: AchievementItem[]
}

export const statsApi = {
  getUserStats(studentId: string): Promise<UserStatsResponse> {
    return request.get(`/stats/user/${studentId}`)
  },
  
  getSkillScores(studentId: string): Promise<SkillScoresResponse> {
    return request.get(`/portrait/${studentId}/skill_scores`)
  },
  
  getCompetitivenessHistory(studentId: string): Promise<CompetitivenessHistoryResponse> {
    return request.get(`/portrait/${studentId}/competitiveness_history`)
  },
  
  getIndustryTrends(): Promise<IndustryTrendsResponse> {
    return request.get('/market/industry_trends')
  },
  
  getAchievements(studentId: string): Promise<AchievementsResponse> {
    return request.get(`/user/${studentId}/achievements`)
  },
}
